"""
FormulaBase Nexus - FastAPI Main Entry Point
Runs locally on port 8765 as a background service for the Electron/Tauri frontend
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from core.config import settings
from database.db import create_all_tables, SessionLocal
from database.seed import seed_database

# ─────────────────────────────────────────────────────────────────
# Import all routers
# ─────────────────────────────────────────────────────────────────
from modules.brands.router import router as brands_router
from modules.erp_formula.router import router as erp_router
from modules.pos_invoice.router import router as pos_router
from modules.accounting.router import router as accounting_router
from modules.pdf_invoice_engine.router import router as pdf_router
from modules.auth.router import router as auth_router

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"   Database: {settings.db_url}")
    logger.info(f"   Templates: {settings.templates_dir}")

    # Initialize database tables
    create_all_tables()
    logger.info("✅ Database tables initialized")

    # Seed demo data if DB is empty
    try:
        db = SessionLocal()
        seeded = seed_database(db)
        if seeded:
            logger.info("✅ Demo data seeded successfully")
        db.close()
    except Exception as e:
        logger.error(f"❌ Error seeding database: {e}")

    logger.info(f"✅ {settings.APP_NAME} ready on http://{settings.API_HOST}:{settings.API_PORT}")
    yield
    logger.info(f"🛑 {settings.APP_NAME} shutting down...")


# ─────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=f"{settings.APP_SUBTITLE} — Complete OEM ERP + Multi-Brand POS with Smart PDF Invoice Engine",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS (allow frontend dev server and Electron)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# Exception handlers
# ─────────────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


# ─────────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth_router,       prefix=f"{API_PREFIX}/auth",       tags=["Authentication"])
app.include_router(brands_router,     prefix=f"{API_PREFIX}/brands",     tags=["Brand Profiles"])
app.include_router(erp_router,        prefix=f"{API_PREFIX}/erp",        tags=["Formula ERP"])
app.include_router(pos_router,        prefix=f"{API_PREFIX}/pos",        tags=["POS & Invoices"])
app.include_router(accounting_router, prefix=f"{API_PREFIX}/accounting", tags=["Auto-Accountant"])
app.include_router(pdf_router,        prefix=f"{API_PREFIX}/pdf",        tags=["PDF Engine"])


# Serve static files (generated invoices, uploads)
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)
app.mount("/data", StaticFiles(directory=data_dir), name="data")


@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "hardware_id": settings.HARDWARE_ID,
        "license_mode": settings.LICENSE_MODE,
    }


@app.get("/api/v1/system/info", tags=["System"])
async def system_info():
    """System information."""
    from database.db import SessionLocal
    from database.models import Company, Brand, Invoice
    db = SessionLocal()
    try:
        company = db.query(Company).first()
        brand_count = db.query(Brand).count()
        invoice_count = db.query(Invoice).count()
        return {
            "company": company.name if company else None,
            "brands": brand_count,
            "total_invoices": invoice_count,
            "hardware_id": settings.HARDWARE_ID,
            "license_mode": settings.LICENSE_MODE,
            "version": settings.APP_VERSION,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
