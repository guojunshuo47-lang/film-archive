"""
Run once before first deploy to create all database tables.

Usage:
    cd backend
    python init_db.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, engine
from app import models  # noqa: F401 — registers all ORM models with Base


async def main():
    os.makedirs("data", exist_ok=True)
    print("Initializing database...")
    await init_db()
    await engine.dispose()
    print("Done. Tables created: users, rolls, photos")


if __name__ == "__main__":
    asyncio.run(main())
