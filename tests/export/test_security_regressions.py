"""
Static security regression tests for crawler TLS handling.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_PATHS = [
    REPO_ROOT / "github_web" / "scripts" / "asset_intelligence" / "fetch_etf_profiles.py",
    REPO_ROOT / "github_web" / "scripts" / "asset_intelligence" / "sources.py",
]
FORBIDDEN_SNIPPETS = (
    "verify=False",
    "TLS_VERIFY_EXCEPTIONS",
    "disable_warnings",
    "# nosec B501",
    "urllib3",
)


def test_asset_profile_fetcher_does_not_disable_tls_verification():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CODE_PATHS)

    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in combined
