import os
import sys
import types
import traceback

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
except Exception as _exc1:
    try:
        from app.main import app
    except Exception as _exc2:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        app = FastAPI(title="Fatal Startup Fallback")
        _tb1 = "".join(traceback.format_exception(_exc1))
        _tb2 = "".join(traceback.format_exception(_exc2))
        _diag_data = {
            "status": "error",
            "source": "server_import_failure",
            "attempt_server_app_main": str(_exc1),
            "attempt_server_app_main_traceback": _tb1.splitlines(),
            "attempt_app_main": str(_exc2),
            "attempt_app_main_traceback": _tb2.splitlines(),
            "sys_path": sys.path,
            "cwd": os.getcwd()
        }
        @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
        async def catch_all(full_path: str):
            return JSONResponse(status_code=500, content=_diag_data)
