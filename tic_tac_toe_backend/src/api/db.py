from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient

from src.api.config import get_mongodb_db_name, get_mongodb_url


async def _init_indexes(db) -> None:
    """Create necessary indexes for collections."""
    await db.players.create_index("username", unique=True)
    await db.games.create_index("created_at")


@asynccontextmanager
# PUBLIC_INTERFACE
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan to initialize and shutdown MongoDB client.

    Initializes:
        - MongoDB AsyncIOMotorClient
        - Database reference on app.state.db
        - Required indexes

    Yields:
        None
    """
    mongo_url = get_mongodb_url()
    db_name = get_mongodb_db_name()

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    app.state.mongo_client = client
    app.state.db = db

    await _init_indexes(db)

    try:
        yield
    finally:
        client.close()


# PUBLIC_INTERFACE
def get_db(request: Request) -> Any:
    """FastAPI dependency to access the MongoDB database handle."""
    return request.app.state.db
