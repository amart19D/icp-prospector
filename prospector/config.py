from __future__ import annotations

from pathlib import Path

import yaml

REQUIRED_SCORING_KEYS = {
    "pain_signal_present",
    "b2b_saas_signals",
    "small_team_signals",
    "helpdesk_stack_detected",
    "docs_present",
}

DEFAULT_SOURCE_RPM = {
    "reddit": 30,
    "hacker_news": 40,
    "x": 20,
    "indie_hackers": 20,
    "product_hunt": 20,
}


def _require_field(section: dict, key: str, section_name: str) -> None:
    if key not in section:
        raise ValueError(f"Missing required field '{section_name}.{key}'")


def _ensure_bool(section: dict, key: str, section_name: str) -> None:
    if key in section and not isinstance(section[key], bool):
        raise ValueError(f"Field '{section_name}.{key}' must be a boolean")


def _validate(config: dict) -> None:
    for top_level in ["icp", "sources", "output", "state"]:
        if top_level not in config:
            raise ValueError(f"Missing required top-level section '{top_level}'")

    icp = config["icp"]
    for key in ["name", "pain_keywords", "exclude_keywords", "scoring"]:
        _require_field(icp, key, "icp")

    if not isinstance(icp["pain_keywords"], list) or not icp["pain_keywords"]:
        raise ValueError("icp.pain_keywords must be a non-empty list")
    if not isinstance(icp["exclude_keywords"], list):
        raise ValueError("icp.exclude_keywords must be a list")
    if not isinstance(icp["scoring"], dict):
        raise ValueError("icp.scoring must be a mapping")

    missing_scoring_keys = REQUIRED_SCORING_KEYS - set(icp["scoring"].keys())
    if missing_scoring_keys:
        missing = ", ".join(sorted(missing_scoring_keys))
        raise ValueError(f"icp.scoring missing required keys: {missing}")

    if "keyword_expansions" in icp:
        if not isinstance(icp["keyword_expansions"], dict):
            raise ValueError("icp.keyword_expansions must be a mapping of keyword -> list[str]")
        for seed, variants in icp["keyword_expansions"].items():
            if not isinstance(seed, str):
                raise ValueError("icp.keyword_expansions keys must be strings")
            if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
                raise ValueError("icp.keyword_expansions values must be list[str]")

    sources = config["sources"]
    for key in ["x", "indie_hackers", "product_hunt", "hacker_news"]:
        _ensure_bool(sources, key, "sources")

    _require_field(sources, "reddit", "sources")
    if not isinstance(sources["reddit"], dict):
        raise ValueError("sources.reddit must be a mapping")
    _require_field(sources["reddit"], "subreddits", "sources.reddit")
    if not isinstance(sources["reddit"]["subreddits"], list):
        raise ValueError("sources.reddit.subreddits must be a list")

    output = config["output"]
    for output_key in ["google_sheets", "csv", "summary"]:
        _require_field(output, output_key, "output")

    state = config["state"]
    _require_field(state, "seen_domains_file", "state")


def _apply_defaults(config: dict) -> dict:
    icp = config["icp"]
    icp.setdefault("keyword_expansions", {})

    config.setdefault("http", {})
    config["http"].setdefault("timeout_seconds", 10)

    sources = config["sources"]
    for source_name, rpm in DEFAULT_SOURCE_RPM.items():
        if source_name == "reddit":
            sources["reddit"].setdefault("requests_per_minute", rpm)
        else:
            if source_name in sources and isinstance(sources[source_name], dict):
                sources[source_name].setdefault("requests_per_minute", rpm)
            else:
                sources.setdefault(f"{source_name}_requests_per_minute", rpm)

    output = config["output"]
    output["csv"].setdefault("path", "output/leads.csv")
    output["summary"].setdefault("mode", "stdout")

    return config


def load_config(path: str = "config/icp.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError("Top-level config must be a YAML mapping")

    _validate(loaded)
    return _apply_defaults(loaded)
