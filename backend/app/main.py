import logging
import sys
import uuid
from pathlib import Path

# Make the shared ML package importable whether run from repo root, backend/, or Docker.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app.api.routes import meta, queue, reconstruct  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.store import get_store  # noqa: E402

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("trafficflowiq")

@asynccontextmanager
async def lifespan(_: FastAPI):
    get_store()  # load models + tables ONCE; requests only do lookups and tiny tree predictions
    yield


app = FastAPI(title="TrafficFlowIQ API", version="1.0.0", lifespan=lifespan,
              description="Freeway queue prediction and traffic-state reconstruction.")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
                   allow_methods=["GET", "POST"], allow_headers=["*"])




@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    rid = uuid.uuid4().hex[:8]
    log.exception("Unhandled error [%s] on %s", rid, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server.", "request_id": rid})


for r in (meta.router, queue.router, reconstruct.router):
    app.include_router(r)
