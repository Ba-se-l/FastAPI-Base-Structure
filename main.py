from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.database import AsyncEngineLocal, create_all_tables
from src.exc import AppException
from src.modules import api_router
from src.settings import settings
from src.share import ErrorDetail, ErrorResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle events.

    On startup: Initializes database tables.
    On shutdown: Closes and disposes engine connection pool.
    """
    logger.info('Initializing application database schema...')
    await create_all_tables()
    logger.info('Application startup complete.')

    yield

    logger.info('Disposing database engine connection pool...')
    await AsyncEngineLocal.dispose()
    logger.info('Application shutdown complete.')


app = FastAPI(
    title=settings.app_title,
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


@app.middleware('http')
async def request_context_middleware(request: Request, call_next):
    """Generates and propagates unique X-Request-ID for request tracing."""
    request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for domain-specific application exceptions.

    Converts AppException into unified ErrorResponse envelope with request_id.
    """
    request_id = getattr(request.state, 'request_id', None)
    logger.warning(
        'AppException [%s] on %s %s: %s (request_id=%s)',
        exc.error_code,
        request.method,
        request.url.path,
        exc.message,
        request_id,
    )
    payload = ErrorResponse(
        success=False,
        error=ErrorDetail(code=exc.error_code, message=exc.message),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for uncaught server errors.

    Logs full stack trace and returns sanitized 500 ErrorResponse envelope.
    """
    request_id = getattr(request.state, 'request_id', None)
    logger.exception(
        'Unhandled server exception on %s %s (request_id=%s): %s',
        request.method,
        request.url.path,
        request_id,
        exc,
    )
    payload = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code='INTERNAL_SERVER_ERROR',
            message='An unexpected server error occurred.',
        ),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=500,
        content=payload.model_dump(),
    )


# Health check endpoints
@app.get('/health', tags=['Health'], summary='Liveness probe')
async def liveness() -> dict[str, str]:
    """Liveness probe confirming application process is running."""
    return {
        'status': 'ok',
        'version': settings.app_version,
        'environment': settings.environment,
    }


@app.get('/health/ready', tags=['Health'], summary='Readiness probe')
async def readiness() -> JSONResponse:
    """Readiness probe verifying database connectivity."""
    try:
        async with AsyncEngineLocal.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return JSONResponse(
            status_code=200,
            content={'status': 'ok', 'checks': {'database': 'ok'}},
        )
    except Exception as exc:
        logger.error('Database readiness probe failed: %s', exc)
        return JSONResponse(
            status_code=503,
            content={'status': 'error', 'checks': {'database': 'unreachable'}},
        )


# Include the master API router
app.include_router(api_router)


if __name__ == '__main__':
    import uvicorn

    # Import string ensures reload functions correctly
    uvicorn.run(
        'main:app',
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
