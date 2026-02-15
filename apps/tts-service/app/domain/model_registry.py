from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class TtsModelDescriptor:
    id: str
    label: str
    languages: list[str]
    voice_presets: list[str]
    default_voice: str
    speed_presets: list[float]


_SPEED_PRESETS: Final[list[float]] = [0.8, 1.0, 1.2, 1.4]

_TTS_MODELS: Final[list[TtsModelDescriptor]] = [
    TtsModelDescriptor(
        id="mlx-community/Kokoro-82M-bf16",
        label="Kokoro",
        languages=["EN", "JA", "ZH", "FR", "ES", "IT", "PT", "HI"],
        voice_presets=["af_heart", "af_bella", "am_adam", "bf_alice", "jm_kumo", "zf_xiaobei"],
        default_voice="af_heart",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
        label="Qwen3-TTS",
        languages=["ZH", "EN", "JA", "KO"],
        voice_presets=["Chelsie", "Ethan", "Serena"],
        default_voice="Chelsie",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/csm-1b",
        label="CSM",
        languages=["EN"],
        voice_presets=["conversational_a", "conversational_b"],
        default_voice="conversational_a",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/Dia-1.6B-fp16",
        label="Dia",
        languages=["EN"],
        voice_presets=["default"],
        default_voice="default",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/OuteTTS-1.0-0.6B-fp16",
        label="OuteTTS",
        languages=["EN"],
        voice_presets=["default"],
        default_voice="default",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/Spark-TTS-0.5B-bf16",
        label="Spark",
        languages=["EN", "ZH"],
        voice_presets=["default"],
        default_voice="default",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/chatterbox-fp16",
        label="Chatterbox",
        languages=["EN", "ES", "FR", "DE", "IT", "PT", "PL", "TR", "RU", "NL", "CS", "AR", "ZH", "JA", "HU", "KO"],
        voice_presets=["default"],
        default_voice="default",
        speed_presets=_SPEED_PRESETS,
    ),
    TtsModelDescriptor(
        id="mlx-community/Soprano-1.1-80M-bf16",
        label="Soprano",
        languages=["EN"],
        voice_presets=["default"],
        default_voice="default",
        speed_presets=_SPEED_PRESETS,
    ),
]


def list_tts_models() -> list[TtsModelDescriptor]:
    return list(_TTS_MODELS)


def get_tts_model(model_id: str) -> TtsModelDescriptor | None:
    for model in _TTS_MODELS:
        if model.id == model_id:
            return model
    return None
