from app.adapters.base import BaseAgentAdapter
from app.adapters.claude_adapter import ClaudeAdapter
from app.adapters.codex_adapter import CodexAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.models.task_context import TaskContext


def _context(*, model_id: str | None = None, reasoning_effort: str | None = None) -> TaskContext:
    return TaskContext(
        task_id="TASK-1",
        task_kind="impl",
        description="desc",
        prior_status="todo",
        metadata={
            "workspace_root": ".",
            "model_id": model_id,
            "reasoning_effort": reasoning_effort,
        },
    )


def test_claude_adapter_includes_model_and_effort() -> None:
    adapter = ClaudeAdapter()
    command = adapter.build_command(_context(model_id="sonnet", reasoning_effort="high"), "prompt")
    assert "--model" in command
    assert "sonnet" in command
    assert "--effort" in command
    assert "high" in command


def test_codex_adapter_includes_reasoning_override() -> None:
    adapter = CodexAdapter()
    command = adapter.build_command(_context(model_id="gpt-5.1-codex", reasoning_effort="medium"), "prompt")
    assert "-m" in command
    assert "gpt-5.1-codex" in command
    assert any(part == 'reasoning_effort="medium"' for part in command)


def test_codex_adapter_strips_transcript_noise_from_stderr() -> None:
    adapter = CodexAdapter()
    _, stderr = adapter.sanitize_outputs(
        "",
        "\n".join([
            "codex",
            "Vou carregar os artefatos canônicos.",
            "exec",
            "\"C:\\Program Files\\PowerShell\\7\\pwsh.exe\" -Command 'Get-Content .roadmap\\\\roadmap.json'",
            "succeeded in 2.10s:",
            "OpenAI Codex v0.107.0 (research preview)",
            "model: gpt-5.4",
            "ERROR: {\"detail\":\"boom\"}",
        ]),
    )
    assert "Vou carregar os artefatos canônicos." not in stderr
    assert "pwsh.exe" not in stderr
    assert "OpenAI Codex v0.107.0" in stderr
    assert "model: gpt-5.4" in stderr
    assert "ERROR:" in stderr


def test_gemini_adapter_generates_temp_settings_for_reasoning_effort() -> None:
    adapter = GeminiAdapter()
    context = _context(model_id="gemini-2.5-pro", reasoning_effort="high")
    runtime_env = adapter.build_env(context, "prompt")
    settings_path = runtime_env["GEMINI_CLI_SYSTEM_SETTINGS_PATH"]
    try:
        assert settings_path
        with open(settings_path, "r", encoding="utf-8") as handle:
            payload = handle.read()
        assert "thinkingBudget" in payload
        assert "8192" in payload
    finally:
        adapter.cleanup_runtime(context, "prompt")


def test_base_adapter_normalizes_audit_payload_aliases() -> None:
    normalized = BaseAgentAdapter._normalize_verification_check({
        "check_id": "IV-006",
        "status": "NA",
        "notes": "No SQL database in codebase",
    })
    assert normalized == {
        "id": "IV-006",
        "status": "not_applicable",
        "title": None,
        "evidence": "No SQL database in codebase",
    }

    file_update = BaseAgentAdapter._normalize_file_update({
        "path": "reports/phase2/results/SEC-015.json",
        "status": "verified",
    })
    assert file_update == {
        "path": "reports/phase2/results/SEC-015.json",
        "content": None,
        "status": "verified",
    }
