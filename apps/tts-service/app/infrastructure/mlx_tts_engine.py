from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path
from threading import RLock
from typing import Any

import numpy as np
import soundfile as sf
from mlx_audio.tts.utils import load_model

from app.domain.entities import ArtifactMeta, TtsSelection


class MlxTtsEngine:
    _QWEN3_VOICE_DESIGN_INSTRUCTS = {
        "chelsie": "A warm and friendly young female voice with clear articulation and medium pitch.",
        "ethan": "A calm and confident adult male voice with medium-low pitch and neutral accent.",
        "serena": "A bright and expressive young female voice with slightly higher pitch and energetic tone.",
    }

    def __init__(self, artifacts_dir: Path, voice_max_bytes: int) -> None:
        self._artifacts_dir = artifacts_dir
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._voice_max_bytes = voice_max_bytes
        self._models: dict[str, Any] = {}
        self._lock = RLock()

    def synthesize(self, text: str, selection: TtsSelection, output_basename: str) -> ArtifactMeta:
        clean_text = self._normalize_text(text)
        chunks = self._chunk_text(clean_text)
        model = self._load_model(selection.model_id)

        sample_rate = getattr(model, "sample_rate", 24_000)
        segments: list[np.ndarray] = []

        for chunk in chunks:
            generation_kwargs = self._build_generation_kwargs(model, selection, chunk)

            results = list(model.generate(**generation_kwargs))
            if not results:
                continue

            sample_rate = getattr(results[0], "sample_rate", sample_rate)
            for result in results:
                audio = np.asarray(result.audio, dtype=np.float32)
                if audio.size:
                    segments.append(audio)

        if not segments:
            raise ValueError("TTS engine produced no audio segments")

        merged = np.concatenate(segments)
        wav_path = self._artifacts_dir / f"{output_basename}.wav"
        sf.write(wav_path, merged, sample_rate)

        ogg_path = self._artifacts_dir / f"{output_basename}.ogg"
        self._convert_audio(wav_path, ogg_path, codec="libopus", bitrate="64k")

        wav_path.unlink(missing_ok=True)

        if ogg_path.stat().st_size <= self._voice_max_bytes:
            return ArtifactMeta(
                path=str(ogg_path),
                kind="voice",
                mime_type="audio/ogg",
                size_bytes=ogg_path.stat().st_size,
            )

        mp3_path = self._artifacts_dir / f"{output_basename}.mp3"
        self._convert_audio(ogg_path, mp3_path, codec="libmp3lame", bitrate="128k")
        ogg_path.unlink(missing_ok=True)

        return ArtifactMeta(
            path=str(mp3_path),
            kind="document",
            mime_type="audio/mpeg",
            size_bytes=mp3_path.stat().st_size,
        )

    def _load_model(self, model_id: str) -> Any:
        with self._lock:
            model = self._models.get(model_id)
            if model is None:
                model = load_model(model_id)
                self._models[model_id] = model
            return model

    def _build_generation_kwargs(self, model: Any, selection: TtsSelection, text_chunk: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"text": text_chunk}
        parameters = inspect.signature(model.generate).parameters

        model_id = selection.model_id.lower()
        is_qwen3_voice_design = "qwen3-tts" in model_id and "voicedesign" in model_id

        if "voice" in parameters and selection.voice and not is_qwen3_voice_design:
            kwargs["voice"] = selection.voice

        if is_qwen3_voice_design and "instruct" in parameters:
            kwargs["instruct"] = self._resolve_qwen3_voice_design_instruct(selection.voice)

        if "speed" in parameters:
            kwargs["speed"] = selection.speed

        if "lang_code" in parameters:
            lang_code = self._resolve_lang_code(selection)
            if lang_code is not None:
                kwargs["lang_code"] = lang_code

        return kwargs

    @staticmethod
    def _resolve_lang_code(selection: TtsSelection) -> str | None:
        model_id = selection.model_id.lower()

        # Kokoro does not accept \"auto\" and expects a short language code.
        if "kokoro" in model_id:
            prefix = (selection.voice or "").strip().lower()[:1]
            supported = {"a", "b", "e", "f", "h", "i", "p", "j", "z"}
            return prefix if prefix in supported else "a"

        # Qwen3-TTS accepts \"auto\" as a default value.
        if "qwen3-tts" in model_id:
            return "auto"

        return None

    def _resolve_qwen3_voice_design_instruct(self, voice: str) -> str:
        normalized = (voice or "").strip().lower()
        if normalized in self._QWEN3_VOICE_DESIGN_INSTRUCTS:
            return self._QWEN3_VOICE_DESIGN_INSTRUCTS[normalized]

        # Allow advanced users to pass a custom voice description directly.
        if normalized and normalized not in {"default", "voice"}:
            return voice

        return self._QWEN3_VOICE_DESIGN_INSTRUCTS["chelsie"]

    @staticmethod
    def _convert_audio(input_path: Path, output_path: Path, codec: str, bitrate: str) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-c:a",
            codec,
            "-b:a",
            bitrate,
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {completed.stderr.strip()}")

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        normalized = re.sub(r"[`*_>#-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 1_500) -> list[str]:
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: list[str] = []
        current = ""

        for sentence in sentences:
            if not sentence:
                continue
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                chunks.append(current)

            if len(sentence) <= max_chars:
                current = sentence
            else:
                parts = [sentence[i : i + max_chars] for i in range(0, len(sentence), max_chars)]
                chunks.extend(parts[:-1])
                current = parts[-1]

        if current:
            chunks.append(current)

        return chunks
