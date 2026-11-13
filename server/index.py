import os
import sys
import types
import traceback

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

for _p in [_parent_dir, _current_dir]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure virtual 'server' package mapping exists
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
    try:
        from app.main import app
    except Exception as exc:
        _tb = traceback.format_exc()
        print(f"CRITICAL BACKEND IMPORT ERROR:\n{_tb}", flush=True)
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        app = FastAPI(title="AgentLink AI (Fallback Mode)")
        
        @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def debug_error(full_path: str):
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Backend failed during module initialization",
                    "details": str(exc),
                    "traceback": _tb.splitlines()
                }
            )
