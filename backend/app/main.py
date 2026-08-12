from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import cases, orders, stats

app = FastAPI(
    title="CIRP Index API",
    description="Evidence-linked index of IBBI insolvency orders",
    version="0.1.0",
)

# Local dev only - the frontend runs on a different port, and the preview
# tooling can reassign that port at random. No auth/user data on this API,
# so allowing any localhost origin doesn't carry the usual CORS risk.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(orders.router)
app.include_router(stats.router)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
