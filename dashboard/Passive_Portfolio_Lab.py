# Compatibility shim for Streamlit Cloud.
# This app was originally deployed with the entry point set to this path.
# The real source lives at streamlit_dashboard/app.py.
# This file re-executes a fixed repo-local app file so Streamlit Cloud can find
# its entry point without requiring a full redeployment (which would lose all
# saved secrets). It never executes user-provided input.
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_app = os.path.join(_root, "streamlit_dashboard", "app.py")

# Ensure project root is on sys.path so all existing imports resolve correctly.
if _root not in sys.path:
    sys.path.insert(0, _root)

with open(_app) as _f:
    exec(compile(_f.read(), _app, "exec"), {"__file__": _app, "__name__": "__main__"})  # nosec B102
