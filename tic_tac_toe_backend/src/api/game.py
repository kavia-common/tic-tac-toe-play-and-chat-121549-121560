from typing import List, Optional, Tuple

from fastapi import HTTPException, status


WIN_COMBOS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


# PUBLIC_INTERFACE
def check_winner(board: List[str]) -> Optional[str]:
    """Check if there is a winner on the board.

    Args:
        board: List of 9 cells with values 'X', 'O', or ''.

    Returns:
        'X' or 'O' if there's a winner, otherwise None.
    """
    for a, b, c in WIN_COMBOS:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


# PUBLIC_INTERFACE
def is_draw(board: List[str]) -> bool:
    """Return True if the board is full and there is no winner."""
    return all(cell in ("X", "O") for cell in board) and check_winner(board) is None


# PUBLIC_INTERFACE
def apply_move(
    game_doc: dict, position: int, player: str
) -> Tuple[dict, str]:
    """Apply a move to the given game doc with validation.

    Args:
        game_doc: Game document dict from database.
        position: 0-based board index (0..8).
        player: 'X' or 'O'.

    Returns:
        Tuple of (updated_game_doc, status_message)

    Raises:
        HTTPException: If move is invalid (bad player, bad position, cell occupied, or game over).
    """
    if game_doc.get("status") != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is already finished with status '{game_doc.get('status')}'.",
        )

    if player not in ("X", "O"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player must be 'X' or 'O'.",
        )

    if player != game_doc.get("current_player"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"It is not {player}'s turn.",
        )

    if position < 0 or position > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position must be between 0 and 8.",
        )

    board = game_doc.get("board", [""] * 9)
    if board[position]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cell {position} is already occupied.",
        )

    # Apply the move
    board[position] = player
    game_doc["board"] = board
    game_doc.setdefault("moves", []).append({"player": player, "position": position})

    winner = check_winner(board)
    if winner:
        game_doc["status"] = f"{winner.lower()}_won"
        game_doc["current_player"] = None
        return game_doc, f"Player {winner} wins!"
    elif is_draw(board):
        game_doc["status"] = "draw"
        game_doc["current_player"] = None
        return game_doc, "It's a draw!"
    else:
        # Switch current player
        game_doc["current_player"] = "O" if player == "X" else "X"
        return game_doc, f"Move accepted. Next: {game_doc['current_player']}"
