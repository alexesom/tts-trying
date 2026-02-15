from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from app.domain.entities import LmSelection


@dataclass(slots=True)
class LmValidationResult:
    valid: bool
    reason: str | None = None


class LmStudioClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def list_models(self) -> list[str]:
        response = requests.get(
            f"{self._base_url}/models",
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        return [item.get("id", "") for item in data if item.get("id")]

    def validate_model(self, model_id: str) -> LmValidationResult:
        attempts = [
            {
                "model": model_id,
                "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
                "temperature": 0,
                "max_tokens": 8,
            },
            {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "source_lang_code": "EN",
                                "target_lang_code": "EN",
                                "text": "Reply with exactly: ok",
                                "image": None,
                            }
                        ],
                    }
                ],
                "temperature": 0,
                "max_tokens": 8,
            },
            {
                "model": model_id,
                "prompt": "Reply with exactly: ok",
                "temperature": 0,
                "max_tokens": 8,
            },
        ]

        errors: list[str] = []

        for index, payload in enumerate(attempts):
            endpoint = "chat/completions" if index < 2 else "completions"
            try:
                response = requests.post(
                    f"{self._base_url}/{endpoint}",
                    json=payload,
                    timeout=self._timeout_seconds,
                )
                if response.status_code >= 400:
                    errors.append(f"{endpoint}: {response.text[:200]}")
                    continue

                text = self._extract_text(response.json())
                if text.strip():
                    return LmValidationResult(valid=True)
                errors.append(f"{endpoint}: empty response")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{endpoint}: {exc}")

        reason = " | ".join(errors)[:1000] if errors else "Unknown validation error"
        return LmValidationResult(valid=False, reason=reason)

    def summarize(self, text: str, selection: LmSelection) -> str:
        prompt = (
            "Summarize the following article in 2-4 concise sentences. "
            "Focus on concrete facts and keep the output plain text.\n\n"
            f"Article:\n{text[:12000]}"
        )
        return self._chat(selection.summary_model_id, prompt)

    def filename(self, text: str, url: str, selection: LmSelection) -> str:
        prompt = (
            "Generate a short filename slug for an audio file from this article. "
            "Rules: lowercase, english letters/numbers/hyphen only, 4-10 words, no extension, no extra text.\n\n"
            f"URL: {url}\n"
            f"Content:\n{text[:4000]}"
        )
        return self._chat(selection.filename_model_id, prompt)

    def _chat(self, model_id: str, prompt: str) -> str:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        response = requests.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        text = self._extract_text(response.json()).strip()
        if not text:
            raise ValueError("LM model returned empty response")
        return text

    @staticmethod
    def _extract_text(payload: dict) -> str:
        choices = payload.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message")
        if message and isinstance(message, dict):
            content = message.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                return " ".join(parts)

        text = choices[0].get("text")
        if isinstance(text, str):
            return text

        return json.dumps(choices[0])
