from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from memory.sqlite import get_sqlite_saver, get_sqlite_store


def initialize_database() -> AbstractAsyncContextManager[AsyncSqliteSaver]:
    """Use SQLite for local LogMind conversation checkpoints."""
    return get_sqlite_saver()


def initialize_store():
    """Use the local in-memory store for the current process."""
    return get_sqlite_store()


__all__ = ["initialize_database", "initialize_store"]
