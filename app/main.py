"""
Main FastAPI application entry point.
Configures database schema initialization, middleware, routes, and OpenAPI documentation.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.api.v1.router import api_router
from app.api.v1.payments import router as payments_root_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("eve_healthcare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for setup and teardown tasks."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
Backend service for diagnostic test bookings and simulated payment processing.

### Features
* **Authentication**: JWT-based user signup & login.
* **Diagnostic Catalog**: Centres, available tests, and centre-specific pricing.
* **Booking System**: Appointment scheduling with price integrity and lifecycle tracking (PENDING, CONFIRMED, FAILED, CANCELLED).
* **Payment Simulation**: Mock payment processing with immediate status updates.
* **Idempotent Webhooks**: Safe payment status synchronization supporting repeat deliveries without side effects.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount primary API router under versioned prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also expose payments directly under /payments to strictly match PDF prompt specifications
app.include_router(payments_root_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
