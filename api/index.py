import sys
import os

_current_file = os.path.abspath(__file__)
_root_dir = os.path.dirname(os.path.dirname(_current_file))
_server_dir = os.path.join(_root_dir, "server")

for _p in [_root_dir, _server_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from server.app.main import app
