# -*- coding: utf-8 -*-
"""
Health check API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Prism2 Backend API is running",
        "version": "1.0.0"
    }


@router.get("/health/database")
async def database_health_check(db: Session = Depends(get_db)):
    """Database health check"""
    try:
        # Test database connection
        db.execute("SELECT 1")

        # Test Redis connection
        redis_client = get_redis()
        redis_client.ping()

        return {
            "status": "ok",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }