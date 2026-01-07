"""Main FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
from socketio import ASGIApp

from app.config import settings
from app.routers import sessions, analysis
from app.sockets.handlers import sio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app (base ASGI app for REST)
fastapi_app = FastAPI(
    title="EchoMind Backend",
    description="AI-powered discussion facilitation system",
    version="0.2.0",
)

# CORS middleware
# If using wildcard origins, credentials must be disabled to satisfy CORS spec
allow_credentials = False if settings.cors_origins == ["*"] else True

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
fastapi_app.include_router(sessions.router)
fastapi_app.include_router(analysis.router)


# Health check endpoint
@fastapi_app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "echomind-backend"}


# Root endpoint
@fastapi_app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "EchoMind Backend",
        "version": "0.2.0",
        "docs_url": "/docs",
    }


# SocketIO integration (wrap FastAPI app with Socket.IO ASGI app)
app = ASGIApp(socketio_server=sio, other_asgi_app=fastapi_app)
