from typing import Optional

from openai import OpenAI
from pydantic import BaseModel

from src.api.config import get_openai_api_key, get_openai_model


class GameContext(BaseModel):
    board: list[str]
    current_player: Optional[str] = None
    players: dict[str, str] = {}
    status: str = "in_progress"


def _board_to_ascii(board: list[str]) -> str:
    def cell(v: str) -> str:
        return v if v in ("X", "O") else " "

    rows = [
        f" {cell(board[0])} | {cell(board[1])} | {cell(board[2])} ",
        "---+---+---",
        f" {cell(board[3])} | {cell(board[4])} | {cell(board[5])} ",
        "---+---+---",
        f" {cell(board[6])} | {cell(board[7])} | {cell(board[8])} ",
    ]
    return "\n".join(rows)


def _fallback_trash_talk(user_message: str, game: Optional[GameContext], username: Optional[str]) -> str:
    name = username or "player"
    board = f"\nBoard:\n{_board_to_ascii(game.board)}" if game else ""
    return f"Nice try, {name}! But that move? Chef's kiss... for me. 😎{board}"


# PUBLIC_INTERFACE
def generate_trash_talk(
    user_message: str,
    game: Optional[dict],
    username: Optional[str] = None,
) -> str:
    """Generate a playful trash talk response using OpenAI if configured.

    If OPENAI_API_KEY is not set, a deterministic fallback message is returned.

    Args:
        user_message: The user's chat message.
        game: Optional current game document to provide context.
        username: Optional username for personalization.

    Returns:
        Trash talk reply string.
    """
    api_key = get_openai_api_key()
    game_ctx = None
    if game:
        game_ctx = GameContext(
            board=game.get("board", [""] * 9),
            current_player=game.get("current_player"),
            players=game.get("players", {}),
            status=game.get("status", "in_progress"),
        )

    if not api_key:
        return _fallback_trash_talk(user_message, game_ctx, username)

    client = OpenAI(api_key=api_key)
    model = get_openai_model()

    system_prompt = (
        "You are a light-hearted, playful trash talker for a Tic Tac Toe game. "
        "Tease and banter without being offensive. Keep responses short (max 2 sentences). "
        "Be witty and fun. If given a board state, you can reference smart observations."
    )

    content_parts = [
        f"User: {username or 'player'}" if username else None,
        f"Message: {user_message}",
    ]

    if game_ctx:
        content_parts.append("Game status: " + game_ctx.status)
        content_parts.append("Current player: " + str(game_ctx.current_player))
        content_parts.append("Players: " + str(game_ctx.players))
        content_parts.append("Board:\n" + _board_to_ascii(game_ctx.board))

    content = "\n".join([p for p in content_parts if p])

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.8,
            max_tokens=80,
        )
        reply = completion.choices[0].message.content or ""
        return reply.strip() or _fallback_trash_talk(user_message, game_ctx, username)
    except Exception:
        # Soft-fail to keep the endpoint responsive if OpenAI is unavailable
        return _fallback_trash_talk(user_message, game_ctx, username)
