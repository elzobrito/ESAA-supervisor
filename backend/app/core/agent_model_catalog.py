from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentModelOption:
    model_id: str
    label: str


@dataclass(frozen=True, slots=True)
class AgentReasoningOption:
    effort_id: str
    label: str


@dataclass(frozen=True, slots=True)
class AgentModelCatalogEntry:
    agent_id: str
    default_model: str
    models: tuple[AgentModelOption, ...]
    default_reasoning_effort: str | None
    reasoning_efforts: tuple[AgentReasoningOption, ...]


class AgentModelCatalog:
    _PROJECT_CONFIG_FILE = "agent-capabilities.json"
    _FALLBACKS: dict[str, tuple[str, tuple[AgentModelOption, ...], str | None, tuple[AgentReasoningOption, ...]]] = {
        "codex": (
            "gpt-5.1-codex",
            (
                AgentModelOption("gpt-5.1-codex", "GPT-5.1 Codex"),
                AgentModelOption("gpt-5.1-codex-mini", "GPT-5.1 Codex Mini"),
                AgentModelOption("codex-auto-balanced", "Codex Auto Balanced"),
                AgentModelOption("codex-auto-thorough", "Codex Auto Thorough"),
            ),
            None,
            (
                AgentReasoningOption("minimal", "Minimal"),
                AgentReasoningOption("low", "Low"),
                AgentReasoningOption("medium", "Medium"),
                AgentReasoningOption("high", "High"),
            ),
        ),
        "claude-code": (
            "sonnet",
            (
                AgentModelOption("sonnet", "Sonnet"),
                AgentModelOption("opus", "Opus"),
                AgentModelOption("claude-sonnet-4-6", "Claude Sonnet 4.6"),
            ),
            None,
            (
                AgentReasoningOption("low", "Low"),
                AgentReasoningOption("medium", "Medium"),
                AgentReasoningOption("high", "High"),
            ),
        ),
        "gemini-cli": (
            "gemini-2.5-pro",
            (
                AgentModelOption("gemini-2.5-pro", "Gemini 2.5 Pro"),
                AgentModelOption("gemini-2.5-flash", "Gemini 2.5 Flash"),
                AgentModelOption("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite"),
                AgentModelOption("auto-gemini-2.5", "Auto Gemini 2.5"),
                AgentModelOption("auto-gemini-3", "Auto Gemini 3"),
                AgentModelOption("gemini-3-pro-preview", "Gemini 3 Pro Preview"),
                AgentModelOption("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"),
                AgentModelOption("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
            ),
            None,
            (
                AgentReasoningOption("low", "Low"),
                AgentReasoningOption("medium", "Medium"),
                AgentReasoningOption("high", "High"),
            ),
        ),
    }

    _ENV_KEYS: dict[str, tuple[str, str]] = {
        "codex": ("ESAA_CODEX_MODELS", "ESAA_CODEX_DEFAULT_MODEL"),
        "claude-code": ("ESAA_CLAUDE_MODELS", "ESAA_CLAUDE_DEFAULT_MODEL"),
        "gemini-cli": ("ESAA_GEMINI_MODELS", "ESAA_GEMINI_DEFAULT_MODEL"),
    }

    @classmethod
    def get_entry(cls, agent_id: str, roadmap_dir: str | None = None) -> AgentModelCatalogEntry:
        default_model, models, default_reasoning_effort, reasoning_efforts = cls._resolve_models(agent_id, roadmap_dir=roadmap_dir)
        return AgentModelCatalogEntry(
            agent_id=agent_id,
            default_model=default_model,
            models=models,
            default_reasoning_effort=default_reasoning_effort,
            reasoning_efforts=reasoning_efforts,
        )

    @classmethod
    def all_entries(cls, roadmap_dir: str | None = None) -> dict[str, AgentModelCatalogEntry]:
        return {
            agent_id: cls.get_entry(agent_id, roadmap_dir=roadmap_dir)
            for agent_id in cls._FALLBACKS
        }

    @classmethod
    def validate_model(cls, agent_id: str, model_id: str | None, roadmap_dir: str | None = None) -> bool:
        if not model_id:
            return True
        entry = cls.get_entry(agent_id, roadmap_dir=roadmap_dir)
        return any(option.model_id == model_id for option in entry.models)

    @classmethod
    def validate_reasoning_effort(cls, agent_id: str, effort_id: str | None, roadmap_dir: str | None = None) -> bool:
        if not effort_id:
            return True
        entry = cls.get_entry(agent_id, roadmap_dir=roadmap_dir)
        return any(option.effort_id == effort_id for option in entry.reasoning_efforts)

    @classmethod
    def default_model_for(cls, agent_id: str, roadmap_dir: str | None = None) -> str | None:
        try:
            return cls.get_entry(agent_id, roadmap_dir=roadmap_dir).default_model
        except KeyError:
            return None

    @classmethod
    def default_reasoning_effort_for(cls, agent_id: str, roadmap_dir: str | None = None) -> str | None:
        try:
            return cls.get_entry(agent_id, roadmap_dir=roadmap_dir).default_reasoning_effort
        except KeyError:
            return None

    @classmethod
    def _resolve_models(
        cls,
        agent_id: str,
        roadmap_dir: str | None = None,
    ) -> tuple[str, tuple[AgentModelOption, ...], str | None, tuple[AgentReasoningOption, ...]]:
        if agent_id not in cls._FALLBACKS:
            raise KeyError(f"Unknown agent catalog: {agent_id}")

        fallback_default, fallback_models, fallback_default_effort, fallback_efforts = cls._FALLBACKS[agent_id]
        project_override = cls._load_project_override(agent_id, roadmap_dir)
        if project_override is not None:
            return project_override

        models_env, default_env = cls._ENV_KEYS[agent_id]
        raw_models = os.getenv(models_env, "").strip()
        if not raw_models:
            return fallback_default, fallback_models, fallback_default_effort, fallback_efforts

        seen: set[str] = set()
        ordered_model_ids: list[str] = []
        for token in raw_models.split(","):
            model_id = token.strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            ordered_model_ids.append(model_id)
        models = tuple(
            AgentModelOption(model_id=item, label=item)
            for item in ordered_model_ids
        )
        if not models:
            return fallback_default, fallback_models, fallback_default_effort, fallback_efforts

        configured_default = os.getenv(default_env, "").strip()
        if configured_default and any(option.model_id == configured_default for option in models):
            return configured_default, models, fallback_default_effort, fallback_efforts
        return models[0].model_id, models, fallback_default_effort, fallback_efforts

    @classmethod
    def _load_project_override(
        cls,
        agent_id: str,
        roadmap_dir: str | None,
    ) -> tuple[str, tuple[AgentModelOption, ...], str | None, tuple[AgentReasoningOption, ...]] | None:
        payload = cls._load_project_config(roadmap_dir)
        if not payload:
            return None

        raw_agents = payload.get("agents")
        if not isinstance(raw_agents, dict):
            return None

        raw_entry = raw_agents.get(agent_id)
        if not isinstance(raw_entry, dict):
            return None

        fallback_default, fallback_models, fallback_default_effort, fallback_efforts = cls._FALLBACKS[agent_id]
        models = cls._normalize_model_options(raw_entry.get("models"))
        reasoning_efforts = cls._normalize_reasoning_options(raw_entry.get("reasoning_efforts"))

        if not models:
            models = fallback_models
        if not reasoning_efforts:
            reasoning_efforts = fallback_efforts

        configured_default = raw_entry.get("default_model")
        default_model = configured_default if isinstance(configured_default, str) and any(option.model_id == configured_default for option in models) else models[0].model_id

        configured_effort = raw_entry.get("default_reasoning_effort")
        if isinstance(configured_effort, str) and any(option.effort_id == configured_effort for option in reasoning_efforts):
            default_reasoning_effort = configured_effort
        else:
            default_reasoning_effort = fallback_default_effort
            if default_reasoning_effort is None and reasoning_efforts:
                default_reasoning_effort = reasoning_efforts[0].effort_id

        return default_model, models, default_reasoning_effort, reasoning_efforts

    @classmethod
    def _load_project_config(cls, roadmap_dir: str | None) -> dict[str, Any]:
        if not roadmap_dir:
            return {}
        config_path = Path(roadmap_dir) / cls._PROJECT_CONFIG_FILE
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _normalize_model_options(raw_options: Any) -> tuple[AgentModelOption, ...]:
        if not isinstance(raw_options, list):
            return ()
        normalized: list[AgentModelOption] = []
        seen: set[str] = set()
        for item in raw_options:
            model_id: str | None = None
            label: str | None = None
            if isinstance(item, str):
                model_id = item.strip()
                label = model_id
            elif isinstance(item, dict):
                raw_model_id = item.get("model_id")
                if isinstance(raw_model_id, str):
                    model_id = raw_model_id.strip()
                raw_label = item.get("label")
                if isinstance(raw_label, str) and raw_label.strip():
                    label = raw_label.strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            normalized.append(AgentModelOption(model_id=model_id, label=label or model_id))
        return tuple(normalized)

    @staticmethod
    def _normalize_reasoning_options(raw_options: Any) -> tuple[AgentReasoningOption, ...]:
        if not isinstance(raw_options, list):
            return ()
        normalized: list[AgentReasoningOption] = []
        seen: set[str] = set()
        for item in raw_options:
            effort_id: str | None = None
            label: str | None = None
            if isinstance(item, str):
                effort_id = item.strip()
                label = effort_id
            elif isinstance(item, dict):
                raw_effort_id = item.get("effort_id")
                if isinstance(raw_effort_id, str):
                    effort_id = raw_effort_id.strip()
                raw_label = item.get("label")
                if isinstance(raw_label, str) and raw_label.strip():
                    label = raw_label.strip()
            if not effort_id or effort_id in seen:
                continue
            seen.add(effort_id)
            normalized.append(AgentReasoningOption(effort_id=effort_id, label=label or effort_id))
        return tuple(normalized)
