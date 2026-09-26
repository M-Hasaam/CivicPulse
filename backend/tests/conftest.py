import os

# Settings require DATABASE_URL; tests never connect, so any well-formed URL works.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@db.invalid:5432/test")
