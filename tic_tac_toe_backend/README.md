# Tic Tac Toe Backend (FastAPI)

This service implements game logic, score persistence in MongoDB, and an optional AI-powered trash-talking chat.

## Environment Variables

The backend reads configurations from environment variables (and a local `.env` file during development). Public interfaces in `src/api/config.py` load these values.

Required:
- MONGODB_URL: Full MongoDB connection string (include authSource if using admin auth)
  - Example (when using provided database container locally):
    - mongodb://appuser:dbuser123@localhost:5000/?authSource=admin
- MONGODB_DB: Target database name
  - Default: myapp (aligns with database container scripts)

Optional:
- OPENAI_API_KEY: If not set, chat endpoint responds with a deterministic playful fallback.
- OPENAI_MODEL: Defaults to gpt-4o-mini

A working `.env.example` is provided in this folder.

## Local Development (with provided database)

1) Start the database and initialize collections:
- See tic_tac_toe_database/README.md
- Defaults in database startup.sh: DB_NAME=myapp, DB_USER=appuser, DB_PASSWORD=dbuser123, DB_PORT=5000

2) Configure backend `.env`:
- Copy `.env.example` to `.env` and adjust as needed
- Ensure MONGODB_URL uses authSource=admin if logging in with users defined in the admin database

3) Run backend:
- uvicorn src.api.main:app --host 0.0.0.0 --port 3001
- Docs at /docs

## Preview / Database Viewer

- The database container includes a simple database viewer (Node/Express) that uses:
  - MONGODB_URL, MONGODB_DB
- In the preview environment, the platform exposes the database viewer at a URL like:
  - https://<host>:5001
- Ensure that the backend MONGODB_URL points to the same MongoDB server accessible in your environment (for local development use localhost:5000 as shown above). The .env file is loaded automatically via python-dotenv.

## Notes

- The backend defaults MONGODB_DB to "myapp" to match the database container's startup defaults.
- Do not hard-code secrets or connection info in code; use environment variables.
