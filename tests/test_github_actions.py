from __future__ import annotations

from pathlib import Path

from watchlist_signal_bot.github_actions import (
    build_workflows,
    load_github_actions_config,
    render_workflow,
    render_workflows,
)


def _repository_config() -> dict:
    return load_github_actions_config(root_dir=Path(__file__).resolve().parents[1])


def test_generated_workflows_match_repository_files():
    root_dir = Path(__file__).resolve().parents[1]
    config = load_github_actions_config(root_dir=root_dir)
    rendered = render_workflows(config)

    for relative_path, content in rendered.items():
        target = root_dir / relative_path
        assert target.read_text(encoding="utf-8") == content


def test_keepalive_workflow_is_generated():
    rendered = render_workflows(_repository_config())
    assert ".github/workflows/keepalive.yml" in rendered


def test_keepalive_workflow_can_push_a_bot_commit():
    content = render_workflows(_repository_config())[".github/workflows/keepalive.yml"]

    assert 'name: "Keepalive Bot Commit"' in content
    assert "  schedule:" in content
    assert 'contents: "write"' in content
    assert 'BOT_NAME: "github-actions[bot]"' in content
    assert 'git commit -m "${COMMIT_MESSAGE}"' in content
    assert 'git push origin "HEAD:${GITHUB_REF_NAME}"' in content


def test_keepalive_workflow_skips_commit_while_repository_is_active():
    content = render_workflows(_repository_config())[".github/workflows/keepalive.yml"]

    assert "idle_days=$(( (now_epoch - last_commit_epoch) / 86400 ))" in content
    assert (
        'if [[ "${FORCE}" != "true" && "${idle_days}" -lt "${INACTIVITY_DAYS}" ]]; then' in content
    )
    assert "        default: false" in content


def test_keepalive_options_come_from_config():
    workflows = build_workflows(
        {
            "keepalive": {
                "schedule": ["30 5 * * 3"],
                "options": {
                    "inactivity_days": 20,
                    "marker_file": "docs/keepalive.txt",
                    "commit_message": "chore: ping",
                },
            }
        }
    )
    content = render_workflow(workflow=workflows["keepalive"])

    assert 'cron: "30 5 * * 3"' in content
    assert "INACTIVITY_DAYS: 20" in content
    assert 'MARKER_FILE: "docs/keepalive.txt"' in content
    assert 'COMMIT_MESSAGE: "chore: ping"' in content


def test_keepalive_options_fall_back_to_defaults():
    workflows = build_workflows({"keepalive": {"options": {"inactivity_days": "not-a-number"}}})
    content = render_workflow(workflow=workflows["keepalive"])

    assert "INACTIVITY_DAYS: 50" in content
    assert 'MARKER_FILE: ".github/keepalive.txt"' in content
