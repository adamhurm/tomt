"""Web service for TOMT music discovery."""

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tomt.web.routes import router

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="TOMT Music Discovery",
    description="Discover songs that people are searching for on Reddit",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routes
app.include_router(router)

# Get the directory of this file for templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def main():
    """Run the web server."""
    host = os.getenv("TOMT_HOST", "0.0.0.0")
    port = int(os.getenv("TOMT_PORT", "8000"))
    reload = os.getenv("TOMT_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "tomt.web:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
