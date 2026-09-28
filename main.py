from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator

from src.settings import settings
from src.database import AsyncEngineLocal, create_all_tables
from src.exc import AppException
from src.modules import api_router



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle events.

    On startup: Connects to the database and creates all tables if
    they don't already exist.
    On shutdown: Closes the database engine.
    """
    
    await create_all_tables()

    yield

    await AsyncEngineLocal.dispose()


app = FastAPI(
    title= settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins, 
    allow_credentials=True,
    allow_methods=settings.allow_methods,
    allow_headers=settings.allowed_headers,
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for all domain-specific application exceptions.

    Converts any ``AppException`` subclass into a standardized JSON response
    containing the error code and message.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for uncaught server errors.

    Prevents leaking internal stack traces to the client in production.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred.",
        },
    )


# Include the master API router
app.include_router(api_router)

# Mount the static frontend interface (commented out until static dir is created)
# app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    # Allows starting the server directly via `python src/main.py`
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
