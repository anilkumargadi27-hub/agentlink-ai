import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

for _p in [_parent_dir, _current_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from server.app.main import app
except Exception:
    from app.main import app
