from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os

from app.config import get_settings
from app.database import init_db
from app.routers import auth, rolls, sync
from app.routers import photos, data as data_router

settings = get_settings()

os.makedirs("uploads", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Film Archive API",
    description="Backend API for Film Archive - A film photography management system",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Return {error, detail} so both api.js (Supabase format) and legacy tests work
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": exc.detail},
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": msg, "detail": exc.errors()},
    )


# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(rolls.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(data_router.router, prefix="/api")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"message": "Film Archive API", "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0", "path": "health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
