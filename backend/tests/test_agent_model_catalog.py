import json
from pathlib import Path

from app.core.agent_model_catalog import AgentModelCatalog


def test_project_capabilities_override_fallbacks(tmp_path: Path) -> None:
    payload = {
        "agents": {
            "codex": {
                "default_model": "GPT-5.4",
                "models": [
                    {"model_id": "GPT-5.4", "label": "GPT-5.4"},
                    {"model_id": "GPT-5.3-Codex", "label": "GPT-5.3-Codex"},
                ],
                "default_reasoning_effort": "medium",
                "reasoning_efforts": [
                    {"effort_id": "low", "label": "Baixa"},
                    {"effort_id": "medium", "label": "Media"},
                    {"effort_id": "very_high", "label": "Altissima"},
                ],
            }
        }
    }
    (tmp_path / "agent-capabilities.json").write_text(json.dumps(payload), encoding="utf-8")

    entry = AgentModelCatalog.get_entry("codex", roadmap_dir=str(tmp_path))

    assert entry.default_model == "GPT-5.4"
    assert [option.model_id for option in entry.models] == ["GPT-5.4", "GPT-5.3-Codex"]
    assert entry.default_reasoning_effort == "medium"
    assert [option.effort_id for option in entry.reasoning_efforts] == ["low", "medium", "very_high"]

