from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.database import AsyncEngineLocal, check_database_connection
from src.exc import AppException
from src.modules import api_router
from src.settings import settings
from src.share import ErrorDetail, ErrorResponse, _HTTP_ERROR_CODE_MAP
from src.share.event_bus import event_bus
from src.modules.audit.listeners import register_audit_listeners

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)



if settings.audit_enabled:
    register_audit_listeners(event_bus)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle events.

    On startup: Verifies database connectivity.
    On shutdown: Closes and disposes engine connection pool.
    """
    logger.info('Verifying database connectivity...')
    await check_database_connection()
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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Global handler for Starlette and FastAPI native HTTPExceptions.

    Intercepts framework-level errors (404 Not Found, 405 Method Not Allowed,
    401 Unauthorized from OAuth2 scheme) and packages them into the unified
    ErrorResponse envelope, ensuring 100% API contract compliance.

    Args:
        request: The incoming HTTP request instance.
        exc: The raised Starlette/FastAPI HTTPException.

    Returns:
        JSONResponse adhering to the unified ErrorResponse schema.
    """
    request_id = getattr(request.state, 'request_id', None)
    logger.warning(
        'HTTPException [%s] on %s %s: %s (request_id=%s)',
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
        request_id,
    )

    default_code = _HTTP_ERROR_CODE_MAP.get(exc.status_code, f"HTTP_{exc.status_code}")
    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message", "An HTTP error occurred."))
        code = str(exc.detail.get('code', default_code))
        details = exc.detail.get('details', None)
    else:
        message = str(exc.detail) if exc.detail else "An HTTP error occurred."
        code = default_code
        details = None

    payload = ErrorResponse(
        success=False,
        error=ErrorDetail(code=code, message=message, details=details),
        request_id=request_id,
    )

    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=payload.model_dump(),
        headers=headers
    )


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Global handler for schema validation errors.

    Wraps FastAPI/Pydantic validation failures in unified ErrorResponse envelope.
    """
    request_id = getattr(request.state, 'request_id', None)
    sanitized_errors = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
    logger.warning(
        'RequestValidationError on %s %s (request_id=%s): %s',
        request.method,
        request.url.path,
        request_id,
        sanitized_errors,
    )
    payload = ErrorResponse(
        success=False,
        error=ErrorDetail(
            code='VALIDATION_ERROR',
            message='Invalid request payload.',
            details=sanitized_errors,
        ),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=422,
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
@app.get(
    '/health',
    tags=['Health'],
    summary='Liveness probe',
    description='Returns raw un-enveloped JSON per Kubernetes liveness probe conventions.',
)
async def liveness() -> dict[str, str]:
    """Liveness probe confirming application process is running.

    Contract Exemption:
        Returns plain JSON (un-enveloped) to satisfy standard container orchestration
        and load-balancer health probe specifications (Kubernetes, AWS ALB, Docker).
    """
    return {
        'status': 'ok',
        'version': settings.app_version,
        'environment': settings.environment.value,
    }


@app.get(
    '/health/ready',
    tags=['Health'],
    summary='Readiness probe',
    description='Returns raw un-enveloped JSON per Kubernetes readiness probe conventions.',
)
async def readiness() -> JSONResponse:
    """Readiness probe verifying database connectivity.

    Contract Exemption:
        Returns plain JSON with standard HTTP 200 or 503 to signal service readiness
        directly to infrastructure ingress/mesh layers without parsing envelope structures.
    """
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
