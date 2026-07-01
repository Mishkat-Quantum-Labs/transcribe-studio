"""HTTP page routes."""

from fastapi import FastAPI

from app.web.routes.dashboard import router as dashboard_router
from app.web.routes.legacy import router as legacy_router
from app.web.routes.projects import router as projects_router
from app.web.routes.recordings_pages import router as recordings_pages_router


def register_page_routes(app: FastAPI) -> None:
    """Mount all HTML page routers on the application."""
    app.include_router(dashboard_router)
    app.include_router(projects_router)
    app.include_router(recordings_pages_router)
    app.include_router(legacy_router)