"""Security regression tests for the FastAPI app."""

from pathlib import Path

import main


class TestFrontendAssetTraversal:
    """``serve_frontend`` must never return a file outside ``dist/``."""

    def test_normal_asset_resolves(self, tmp_path, monkeypatch):
        dist = tmp_path / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "assets" / "app.js").write_text("ok")
        monkeypatch.setattr(main, "FRONTEND_DIST", dist.resolve())

        got = main.resolve_frontend_asset("assets/app.js")

        assert got == (dist / "assets" / "app.js").resolve()

    def test_dotdot_escape_is_rejected(self, tmp_path, monkeypatch):
        root = tmp_path
        (root / "secret.txt").write_text("BASIC_AUTH_PASS=hunter2")
        dist = root / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<html></html>")
        monkeypatch.setattr(main, "FRONTEND_DIST", dist.resolve())

        for attack in (
            "../secret.txt",
            "../../secret.txt",
            "..%2f..%2fsecret.txt",  # FastAPI has already %-decoded by here
            "assets/../../secret.txt",
            "/etc/passwd",
            "../dist/../secret.txt",
        ):
            assert main.resolve_frontend_asset(attack) is None, attack

    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        dist = tmp_path / "dist"
        dist.mkdir()
        monkeypatch.setattr(main, "FRONTEND_DIST", dist.resolve())

        assert main.resolve_frontend_asset("does-not-exist.js") is None
        assert main.resolve_frontend_asset("") is None


def test_env_and_tokens_are_gitignored():
    """The .env and OAuth token files may exist locally, but must stay
    out of version control - guards against an accidental ``git add``."""
    repo = Path(main.__file__).resolve().parent.parent
    gitignore = (repo / ".gitignore").read_text()
    assert ".env" in gitignore
    assert "tokens" in gitignore
