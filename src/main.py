from pathlib import Path
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import DatabaseManager
from .services.inventory import InsufficientStockError
from .routers import ingredients, recipes, suppliers, waybills, currency, pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartbaku")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing DatabaseManager connection pool...")
    db_manager = DatabaseManager(settings)
    app.state.db = db_manager
    yield
    # Shutdown
    logger.info("Closing DatabaseManager connection pool...")
    db_manager.close_pool()

app = FastAPI(
    title="SmartBaku HoReCa ERP",
    version="1.0.0",
    description="Enterprise Resource Planning System for Azerbaijani Hotels, Restaurants, and Cafés",
    lifespan=lifespan
)

# --- Global Exception Handlers ---
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=detail
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(detail),
            "code": "HTTP_ERROR",
            "details": {}
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Request validation failed",
            "code": "VALIDATION_ERROR",
            "details": {"errors": exc.errors()}
        }
    )

@app.exception_handler(InsufficientStockError)
async def insufficient_stock_handler(request: Request, exc: InsufficientStockError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": str(exc),
            "code": "INSUFFICIENT_STOCK",
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected internal server error occurred",
            "code": "DB_ERROR",
            "details": {"message": str(exc)}
        }
    )

# --- Mount Static Files ---
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- Include Routers ---
app.include_router(pages.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)
app.include_router(suppliers.router)
app.include_router(waybills.router)
app.include_router(currency.router)

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "system": "SmartBaku HoReCa ERP"}
