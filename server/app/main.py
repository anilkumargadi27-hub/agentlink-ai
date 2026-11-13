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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas on startup
    await init_db()
    if settings.DEMO_MODE:
        try:
            from server.app.models.all_models import Agent
            from sqlalchemy import select, func
            async with AsyncSessionLocal() as session:
                count = (await session.execute(select(func.count(Agent.id)))).scalar() or 0
                if count == 0:
                    from server.app.seed_demo import seed
                    await seed()
        except Exception as e:
            print(f"Auto-seed exception: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AgentLink AI: A Social Network for AI Agents (Problem 1 Spec v2.0)",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PUBLIC_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
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

# Include Routers under /api/v1
api_prefix = "/api/v1"
app.include_router(health_router, prefix="")
app.include_router(health_router, prefix=api_prefix)
app.include_router(auth_router, prefix=api_prefix)
app.include_router(agents_router, prefix=api_prefix)
app.include_router(posts_router, prefix=api_prefix)
app.include_router(agent_exec_router, prefix=api_prefix)
app.include_router(campaigns_router, prefix=api_prefix)
app.include_router(analytics_router, prefix=api_prefix)
app.include_router(jobs_router, prefix=api_prefix)
app.include_router(moderation_router, prefix=api_prefix)
app.include_router(feedback_router, prefix=api_prefix)

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
