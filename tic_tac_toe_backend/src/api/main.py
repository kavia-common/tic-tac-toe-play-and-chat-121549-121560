from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import get_db, lifespan
from src.api.game import apply_move
from src.api.models import (
    ChatRequest,
    ChatResponse,
    GameCreate,
    GameOut,
    Message,
    MoveRequest,
    MoveResponse,
    PlayerScore,
    PlayerScoreUpdate,
)
from src.api.openai_client import generate_trash_talk


def _serialize_game(doc: Dict[str, Any]) -> GameOut:
    """Convert a MongoDB game document to a GameOut model."""
    return GameOut(
        id=str(doc["_id"]),
        board=doc["board"],
        current_player=doc.get("current_player"),
        players=doc.get("players", {}),
        status=doc.get("status", "in_progress"),
        moves=doc.get("moves", []),
        created_at=doc.get("created_at", datetime.utcnow()),
    )


# OpenAPI tags
openapi_tags = [
    {
        "name": "Health",
        "description": "Service health and diagnostics.",
    },
    {
        "name": "Games",
        "description": "Create games, retrieve games, and make moves.",
    },
    {
        "name": "Scores",
        "description": "Manage and retrieve player scores.",
    },
    {
        "name": "Chat",
        "description": "Send chat messages and get AI trash talk replies.",
    },
]

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description=(
        "Backend service for Tic Tac Toe with persistent scores and an AI trash-talking chat. "
        "This API provides endpoints to manage games, submit moves, track player scores, and chat."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Message, tags=["Health"], summary="Health Check", description="Simple health endpoint to verify the service is running.")
# PUBLIC_INTERFACE
def health_check() -> Message:
    """Health check endpoint."""
    return Message(message="Healthy")


@app.post(
    "/games",
    response_model=GameOut,
    tags=["Games"],
    summary="Create a new game",
    description="Create a new Tic Tac Toe game with optional player names for X and O.",
    status_code=status.HTTP_201_CREATED,
)
# PUBLIC_INTERFACE
async def create_game(payload: GameCreate, db=Depends(get_db)) -> GameOut:
    """Create a new game and return its state."""
    doc = {
        "board": [""] * 9,
        "current_player": "X",
        "players": {"X": payload.player_x, "O": payload.player_o},
        "status": "in_progress",
        "moves": [],
        "created_at": datetime.utcnow(),
    }
    result = await db.games.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_game(doc)


@app.get(
    "/games/{game_id}",
    response_model=GameOut,
    tags=["Games"],
    summary="Get a game by ID",
    description="Retrieve the current state of a game by its ID.",
)
# PUBLIC_INTERFACE
async def get_game(
    game_id: str = Path(..., description="Game identifier."),
    db=Depends(get_db),
) -> GameOut:
    """Retrieve a game by ID."""
    try:
        oid = ObjectId(game_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid game id.")
    doc = await db.games.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return _serialize_game(doc)


@app.post(
    "/games/{game_id}/move",
    response_model=MoveResponse,
    tags=["Games"],
    summary="Submit a move",
    description="Submit a move for a specific game. Validates the move, updates the board, and resolves the game if finished.",
)
# PUBLIC_INTERFACE
async def make_move(
    payload: MoveRequest,
    game_id: str = Path(..., description="Game identifier."),
    db=Depends(get_db),
) -> MoveResponse:
    """Submit a move and update the game state."""
    try:
        oid = ObjectId(game_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid game id.")
    doc = await db.games.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")

    updated_doc, status_message = apply_move(doc, payload.position, payload.player)

    # Persist the update
    # IMPORTANT: Do not attempt to $set the entire document including _id, which is immutable.
    # Instead, only update the fields that can change as a result of a move.
    update_fields = {
        "board": updated_doc.get("board"),
        "current_player": updated_doc.get("current_player"),
        "status": updated_doc.get("status"),
        "moves": updated_doc.get("moves", []),
    }
    await db.games.update_one({"_id": oid}, {"$set": update_fields})

    # If game ended, update scores
    if updated_doc.get("status") in ("x_won", "o_won"):
        winner_symbol = "X" if updated_doc["status"] == "x_won" else "O"
        winner_username = updated_doc.get("players", {}).get(winner_symbol)
        if winner_username:
            await db.players.update_one(
                {"username": winner_username},
                {"$inc": {"score": 1}},
                upsert=True,
            )

    # Return fresh copy
    fresh = await db.games.find_one({"_id": oid})
    return MoveResponse(game=_serialize_game(fresh), status_message=status_message)


@app.get(
    "/scores",
    response_model=List[PlayerScore],
    tags=["Scores"],
    summary="Top scores",
    description="Get the top player scores.",
)
# PUBLIC_INTERFACE
async def get_top_scores(
    limit: int = Query(10, ge=1, le=100, description="Number of top scores to return."),
    db=Depends(get_db),
) -> List[PlayerScore]:
    """Return the top N scores."""
    cursor = db.players.find({}, sort=[("score", -1), ("username", 1)], limit=limit)
    scores: List[PlayerScore] = []
    async for p in cursor:
        scores.append(PlayerScore(username=p["username"], score=int(p.get("score", 0))))
    return scores


@app.get(
    "/scores/{username}",
    response_model=PlayerScore,
    tags=["Scores"],
    summary="Get a player's score",
    description="Retrieve a specific player's score by username.",
)
# PUBLIC_INTERFACE
async def get_player_score(
    username: str = Path(..., description="Player username."),
    db=Depends(get_db),
) -> PlayerScore:
    """Retrieve a player's score."""
    p = await db.players.find_one({"username": username})
    if not p:
        # Default score 0 for new players
        return PlayerScore(username=username, score=0)
    return PlayerScore(username=username, score=int(p.get("score", 0)))


@app.put(
    "/scores/{username}",
    response_model=PlayerScore,
    tags=["Scores"],
    summary="Set a player's score",
    description="Set or update a player's score.",
)
# PUBLIC_INTERFACE
async def set_player_score(
    payload: PlayerScoreUpdate,
    username: str = Path(..., description="Player username."),
    db=Depends(get_db),
) -> PlayerScore:
    """Set a player's score to a specific value."""
    await db.players.update_one(
        {"username": username},
        {"$set": {"score": int(payload.score)}},
        upsert=True,
    )
    p = await db.players.find_one({"username": username})
    return PlayerScore(username=p["username"], score=int(p.get("score", 0)))


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Send a chat message",
    description="Send a chat message and receive a playful trash talk reply generated by OpenAI.",
)
# PUBLIC_INTERFACE
async def chat(
    payload: ChatRequest,
    db=Depends(get_db),
) -> ChatResponse:
    """Process a chat message and return an AI-generated trash talk reply.

    If OpenAI is not configured, returns a deterministic playful response.
    """
    game_doc: Optional[Dict[str, Any]] = None
    if payload.game_id:
        try:
            oid = ObjectId(payload.game_id)
            game_doc = await db.games.find_one({"_id": oid})
        except Exception:
            game_doc = None

    reply = generate_trash_talk(payload.message, game_doc, payload.username)
    return ChatResponse(reply=reply)
