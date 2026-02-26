from pathlib import Path

import pytest

from prospector.config import load_config


def test_load_config_valid(tmp_path: Path) -> None:
    cfg_path = tmp_path / "icp.yaml"
    cfg_path.write_text(
        """
icp:
  name: Test ICP
  pain_keywords: ["support is killing me"]
  exclude_keywords: []
  scoring:
    pain_signal_present: 30
    b2b_saas_signals: 25
    small_team_signals: 20
    helpdesk_stack_detected: 15
    docs_present: 10
sources:
  x: false
  reddit:
    subreddits: [SaaS]
  indie_hackers: false
  product_hunt: false
  hacker_news: true
output:
  google_sheets:
    enabled: false
    sheet_id: ""
    tab_name: Prospects
  csv:
    enabled: true
    path: output/leads.csv
  summary:
    enabled: true
    mode: stdout
state:
  seen_domains_file: state/seen_domains.json
""",
        encoding="utf-8",
    )

    config = load_config(str(cfg_path))
    assert config["icp"]["name"] == "Test ICP"


def test_load_config_missing_required(tmp_path: Path) -> None:
    cfg_path = tmp_path / "bad.yaml"
    cfg_path.write_text("icp: {}\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(str(cfg_path))
