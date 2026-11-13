import os
import sys
import types

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

for _p in [_parent_dir, _current_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# If 'server' module is not resolvable (e.g. running inside server directory as root on Vercel),
# create virtual 'server' package mapping to _current_dir
if "server" not in sys.modules:
    try:
        import app
        _sm = types.ModuleType("server")
        _sm.__path__ = [_current_dir]
        _sm.app = app
        sys.modules["server"] = _sm
        sys.modules["server.app"] = app
    except Exception as _e:
        print(f"Warning: failed to alias server module: {_e}")

try:
    from server.app.main import app
except ImportError:
    from app.main import app
