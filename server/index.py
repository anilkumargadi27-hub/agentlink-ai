import os
import sys
import types

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

for _p in [_parent_dir, _current_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

if "server" not in sys.modules:
    try:
        _sm = types.ModuleType("server")
        _sm.__path__ = [_current_dir]
        sys.modules["server"] = _sm
    except Exception as _e:
        print(f"Warning: failed to alias server module: {_e}", flush=True)

try:
    from server.app.main import app
except Exception:
    from app.main import app
