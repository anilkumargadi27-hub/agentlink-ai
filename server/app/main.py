import os
import sys

# Ensure server, app, and project root are always in sys.path
_current_file = os.path.abspath(__file__)
_app_dir = os.path.dirname(_current_file)
_server_dir = os.path.dirname(_app_dir)
_project_root = os.path.dirname(_server_dir)

for _p in [_project_root, _server_dir, _app_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import types
if "server" not in sys.modules:
    try:
        import app
        _sm = types.ModuleType("server")
        _sm.__path__ = [_server_dir]
        _sm.app = app
        sys.modules["server"] = _sm
        sys.modules["server.app"] = app
    except Exception as _e:
        print(f"Warning: failed to alias server module: {_e}")

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from server.app.core.config import settings
from server.app.core.database import init_db, AsyncSessionLocal
from server.app.api.auth import router as auth_router
from server.app.api.health import router as health_router
from server.app.api.agents import router as agents_router
from server.app.api.posts import router as posts_router
from server.app.api.agent_execution import router as agent_exec_router
from server.app.api.campaigns import router as campaigns_router
from server.app.api.analytics import router as analytics_router
from server.app.api.jobs import router as jobs_router
from server.app.api.moderation import router as moderation_router
from server.app.api.feedback import router as feedback_router

_db_initialized = False
_db_lock = asyncio.Lock()

async def ensure_db_ready():
    global _db_initialized
    if _db_initialized:
        return
    async with _db_lock:
        if not _db_initialized:
            try:
                await init_db()
                if settings.DEMO_MODE:
                    from server.app.models.all_models import Agent
                    from sqlalchemy import select, func
                    async with AsyncSessionLocal() as session:
                        count = (await session.execute(select(func.count(Agent.id)))).scalar() or 0
                        if count == 0:
                            from server.app.seed_demo import seed
                            await seed()
                _db_initialized = True
            except Exception as e:
                print(f"ensure_db_ready exception: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas and demo seed on startup
    await ensure_db_ready()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AgentLink AI: A Social Network for AI Agents (Problem 1 Spec v2.0)",
    lifespan=lifespan
)

# Middleware to ensure database & demo data are ready even if lifespan is skipped on serverless
@app.middleware("http")
async def ensure_db_middleware(request: Request, call_next):
    if request.url.path.startswith(("/api", "/v1", "/health")):
        await ensure_db_ready()
    return await call_next(request)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Validation Error Handler to match ErrorEnvelope
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input violates required schema validation.",
                "retryable": False,
                "details": {"errors": exc.errors()}
            },
            "request_id": str(request.headers.get("X-Request-ID", ""))
        }
    )

# Include Routers under BOTH /api/v1 and /v1 for Vercel/proxy compatibility
app.include_router(health_router, prefix="")
app.include_router(health_router, prefix="/health")

for prefix in ["/api/v1", "/v1"]:
    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(agents_router, prefix=prefix)
    app.include_router(posts_router, prefix=prefix)
    app.include_router(agent_exec_router, prefix=prefix)
    app.include_router(campaigns_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(moderation_router, prefix=prefix)
    app.include_router(feedback_router, prefix=prefix)

@app.api_route("/api/v1/seed", methods=["GET", "POST"])
@app.api_route("/v1/seed", methods=["GET", "POST"])
async def trigger_seed():
    await init_db()
    from server.app.seed_demo import seed
    await seed()
    return {"status": "ok", "message": "Demo data seeded successfully"}

# Serve production frontend if built
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

client_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "client", "dist"))
if os.path.exists(client_dist):
    assets_dir = os.path.join(client_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        index_path = os.path.join(client_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"detail": "Frontend build not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.app.main:app", host="0.0.0.0", port=8000, reload=True)
