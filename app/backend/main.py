"""FastAPI application entry point for the starter kit backend.

This backend serves as the API layer between the React frontend and
Azure Blob Storage / the existing Azure Durable Functions pipeline.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes.upload import router as upload_router
from routes.images import router as images_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Starter Kit UI API",
    description="Starter kit image processing API (Phase 1)",
    version="1.0.0",
)

# CORS — allow the React frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register route modules
app.include_router(upload_router)
app.include_router(images_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
