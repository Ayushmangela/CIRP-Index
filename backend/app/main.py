from typing import Dict

from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="CIRP Index API",
    description="Evidence-linked index of IBBI insolvency orders",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
