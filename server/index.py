import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

for p in [_parent_dir, _current_dir, os.path.join(_current_dir, "app")]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from server.app.main import app
except ImportError:
    from app.main import app
