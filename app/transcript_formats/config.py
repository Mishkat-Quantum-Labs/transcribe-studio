"""Load transcript format settings from TOML."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from app.paths import CONFIG_DIR

FORMATS_PATH = CONFIG_DIR / "transcript_formats.toml"


@dataclass
class FormatConfig:
    id: str
    name: str = ""
    description: str = ""
    enabled: bool = True
    extensions: list[str] = field(default_factory=list)
    example: str = ""


@dataclass
class UploadConfig:
    accepted_extensions: list[str] = field(
        default_factory=lambda: [".json", ".txt", ".transcript"]
    )
    max_bytes: int = 5_242_880


@dataclass
class TranscriptFormatsConfig:
    detection_order: list[str] = field(default_factory=list)
    include_speaker_in_alignment: bool = False
    upload: UploadConfig = field(default_factory=UploadConfig)
    formats: dict[str, FormatConfig] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, path: Path | None = None) -> "TranscriptFormatsConfig":
        path = path or FORMATS_PATH
        if not path.exists():
            return cls(
                detection_order=["timestamp_speaker", "json_segments", "plain_text"],
                formats={},
            )

        with open(path, "rb") as f:
            data = tomllib.load(f)

        root = data.get("transcript_formats", {})
        detection_order = root.get("detection_order", [])
        include_speaker = root.get("alignment", {}).get("include_speaker", False)
        upload_data = root.get("upload", {})
        upload = UploadConfig(
            accepted_extensions=upload_data.get(
                "accepted_extensions", [".json", ".txt", ".transcript"]
            ),
            max_bytes=int(upload_data.get("max_bytes", 5_242_880)),
        )

        formats: dict[str, FormatConfig] = {}
        for fmt_id, fmt_data in root.get("formats", {}).items():
            formats[fmt_id] = FormatConfig(
                id=fmt_id,
                name=fmt_data.get("name", fmt_id),
                description=fmt_data.get("description", ""),
                enabled=fmt_data.get("enabled", True),
                extensions=fmt_data.get("extensions", []),
                example=fmt_data.get("example", ""),
            )

        return cls(
            detection_order=detection_order,
            include_speaker_in_alignment=include_speaker,
            upload=upload,
            formats=formats,
        )


_config: TranscriptFormatsConfig | None = None


def get_transcript_config() -> TranscriptFormatsConfig:
    global _config
    if _config is None:
        _config = TranscriptFormatsConfig.from_toml()
    return _config