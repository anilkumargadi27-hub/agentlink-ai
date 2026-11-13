import sys
import os
import traceback

_current_file = os.path.abspath(__file__)
_root_dir = os.path.dirname(os.path.dirname(_current_file))
_server_dir = os.path.join(_root_dir, "server")

for _p in [_root_dir, _server_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

app = None
import_error = None

try:
    from server.app.main import app as _real_app
    app = _real_app
except Exception as _e:
    import_error = traceback.format_exc()

if app is None:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def debug_route(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend import failed",
                "traceback": import_error.splitlines() if import_error else None
            }
        )
