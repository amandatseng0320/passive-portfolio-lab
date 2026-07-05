"""
Tests for asset profile page fetch helpers.

These tests do not call external websites.
"""

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "github_web" / "scripts" / "asset_intelligence"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fetch_etf_profiles import looks_like_blocked_page


BLOCKED_HTML = """
<html>
  <head><title></title></head>
  <body>FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED. Please contact administrator.</body>
</html>
"""


def test_waf_block_page_detection_uses_multiple_signals():
    assert looks_like_blocked_page(BLOCKED_HTML, "0050.TW")


def test_waf_block_page_detection_does_not_reject_relevant_title():
    html = """
    <html>
      <head><title>0050 ETF profile</title></head>
      <body>Risk note: orders may be blocked during market disruption.</body>
    </html>
    """

    assert not looks_like_blocked_page(html, "0050.TW")
