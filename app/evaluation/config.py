"""
Configuration loader for evaluation settings.
Loads TOML configs and provides a typed Config object.
"""
import tomllib
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


from app.paths import CONFIG_DIR

LANGUAGES_DIR = CONFIG_DIR / "languages"


@dataclass
class MetricConfig:
    """Configuration for a single metric."""
    enabled: bool = True
    weight: float = 1.0


@dataclass
class NormalizationConfig:
    """Configuration for text normalization."""
    lowercase: bool = True
    trim_whitespace: bool = True
    remove_punctuation: bool = False
    normalize_quotes: bool = True
    remove_special_chars: bool = False


@dataclass
class SemanticRule:
    """A single semantic matching rule."""
    variants: list[str] = field(default_factory=list)
    canonical: str = ""
    weight: float = 1.0
    pattern: str = ""  # Optional regex pattern


@dataclass
class SemanticGroup:
    """A group of semantic rules."""
    name: str = ""
    description: str = ""
    enabled: bool = True
    rules: list[SemanticRule] = field(default_factory=list)


@dataclass
class LanguageConfig:
    """Language-specific configuration."""
    code: str = "en"
    name: str = "English"
    semantic_matchers: list[SemanticGroup] = field(default_factory=list)
    normalizer_class: str = "en"  # Maps to normalizers/en.py


@dataclass
class EvaluationConfig:
    """Root evaluation configuration."""
    default_language: str = "en"
    version: str = "1.0"
    metrics: dict[str, MetricConfig] = field(default_factory=dict)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    languages: dict[str, LanguageConfig] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, config_path: Path | None = None) -> "EvaluationConfig":
        """Load configuration from TOML file."""
        if config_path is None:
            config_path = CONFIG_DIR / "evaluation.toml"

        if not config_path.exists():
            return cls._default()

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Parse metrics
        metrics = {}
        metrics_data = data.get("evaluation", {}).get("metrics", {})
        for name, cfg in metrics_data.items():
            if isinstance(cfg, dict):
                metrics[name] = MetricConfig(
                    enabled=cfg.get("enabled", True),
                    weight=cfg.get("weight", 1.0),
                )
            else:
                metrics[name] = MetricConfig(enabled=True, weight=1.0)

        # Parse normalization
        norm_data = data.get("evaluation", {}).get("normalization", {})
        normalization = NormalizationConfig(
            lowercase=norm_data.get("lowercase", True),
            trim_whitespace=norm_data.get("trim_whitespace", True),
            remove_punctuation=norm_data.get("remove_punctuation", False),
            normalize_quotes=norm_data.get("normalize_quotes", True),
            remove_special_chars=norm_data.get("remove_special_chars", False),
        )

        # Parse language configs
        languages = {}
        if LANGUAGES_DIR.exists():
            for lang_file in LANGUAGES_DIR.glob("*.toml"):
                lang_code = lang_file.stem
                lang_cfg = cls._load_language(lang_file)
                languages[lang_code] = lang_cfg

        return cls(
            default_language=data.get("evaluation", {}).get("default_language", "en"),
            version=data.get("evaluation", {}).get("version", "1.0"),
            metrics=metrics,
            normalization=normalization,
            languages=languages,
        )

    @classmethod
    def _load_language(cls, path: Path) -> LanguageConfig:
        """Load a language configuration file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        lang_data = data.get("language", {})
        groups_data = data.get("semantic_matchers", {}).get("group", [])

        # Handle single group (not in list)
        if isinstance(groups_data, dict):
            groups_data = [groups_data]

        semantic_groups = []
        for g_data in groups_data:
            rules = []
            for r_data in g_data.get("rule", []):
                rules.append(SemanticRule(
                    variants=r_data.get("variants", []),
                    canonical=r_data.get("canonical", ""),
                    weight=r_data.get("weight", 1.0),
                    pattern=r_data.get("pattern", ""),
                ))

            semantic_groups.append(SemanticGroup(
                name=g_data.get("name", ""),
                description=g_data.get("description", ""),
                enabled=g_data.get("enabled", True),
                rules=rules,
            ))

        return LanguageConfig(
            code=lang_data.get("code", path.stem),
            name=lang_data.get("name", path.stem),
            semantic_matchers=semantic_groups,
            normalizer_class=lang_data.get("normalizer_class", path.stem),
        )

    @classmethod
    def _default(cls) -> "EvaluationConfig":
        """Return default configuration."""
        return cls(
            default_language="en",
            version="1.0",
            metrics={
                "wer": MetricConfig(enabled=True, weight=1.0),
                "cer": MetricConfig(enabled=False, weight=0.0),
                "semantic_score": MetricConfig(enabled=True, weight=0.5),
            },
            normalization=NormalizationConfig(),
            languages={},
        )

    def get_language_config(self, lang_code: str | None = None) -> LanguageConfig:
        """Get language config, falling back to default."""
        code = lang_code or self.default_language
        if code in self.languages:
            return self.languages[code]
        # Return minimal default
        return LanguageConfig(code=code, name=code)


# Global config instance (lazy loaded)
_config: EvaluationConfig | None = None


def get_config() -> EvaluationConfig:
    """Get the global evaluation configuration."""
    global _config
    if _config is None:
        _config = EvaluationConfig.from_toml()
    return _config


def reload_config() -> EvaluationConfig:
    """Force reload of configuration."""
    global _config
    _config = EvaluationConfig.from_toml()
    return _config
