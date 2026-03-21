from __future__ import annotations

from pathlib import Path

from watchlist_signal_bot.github_actions import load_github_actions_config, render_workflows


def test_generated_workflows_match_repository_files():
    root_dir = Path(__file__).resolve().parents[1]
    config = load_github_actions_config(root_dir=root_dir)
    rendered = render_workflows(config)

    for relative_path, content in rendered.items():
        target = root_dir / relative_path
        assert target.read_text(encoding="utf-8") == content
