from __future__ import annotations

import contextlib
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row


# PUBLIC_INTERFACE
def get_dsn() -> str:
    """
    Return the PostgreSQL DSN string for connecting to the database.

    Note:
        As per requirements, we use the fixed DSN:
        postgresql://appuser:dbuser123@localhost:5000/myapp

        For production usage, consider using environment variables and
        secure secret management instead of hardcoding.
    """
    # Requirement explicitly specifies this DSN and port 5000.
    return "postgresql://appuser:dbuser123@localhost:5000/myapp"


def _connect() -> psycopg.Connection:
    """
    Internal: return a new psycopg connection with secure defaults.
    """
    # autocommit False, use context managers to ensure cleanup.
    return psycopg.connect(get_dsn())


# PUBLIC_INTERFACE
def ensure_schema() -> None:
    """
    Ensure the todos table exists with the expected schema.

    This function is idempotent and safe to call multiple times.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS todos (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
        description TEXT DEFAULT '',
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    trigger_fn = """
    CREATE OR REPLACE FUNCTION set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    trigger_stmt = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_trigger WHERE tgname = 'todos_set_updated_at'
        ) THEN
            CREATE TRIGGER todos_set_updated_at
            BEFORE UPDATE ON todos
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        END IF;
    END $$;
    """
    with contextlib.closing(_connect()) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(trigger_fn)
            cur.execute(trigger_stmt)


# PUBLIC_INTERFACE
def query_all_todos() -> List[Dict[str, Any]]:
    """
    Retrieve all todos ordered by id ascending.
    """
    sql = """
        SELECT id, title, description, completed, created_at, updated_at
        FROM todos
        ORDER BY id ASC
    """
    with contextlib.closing(_connect()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


# PUBLIC_INTERFACE
def query_todo_by_id(todo_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single todo by id.

    Args:
        todo_id: The id of the todo to fetch.

    Returns:
        A dictionary of the todo or None if not found.
    """
    sql = """
        SELECT id, title, description, completed, created_at, updated_at
        FROM todos
        WHERE id = %s
        LIMIT 1
    """
    with contextlib.closing(_connect()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (todo_id,))
            row = cur.fetchone()
            return dict(row) if row else None


# PUBLIC_INTERFACE
def insert_todo(title: str, description: str = "", completed: bool = False) -> Dict[str, Any]:
    """
    Insert a new todo.

    Args:
        title: The title of the todo (1..200 chars).
        description: Optional description.
        completed: Initial completion state.

    Returns:
        The newly inserted row as a dictionary.
    """
    sql = """
        INSERT INTO todos (title, description, completed)
        VALUES (%s, %s, %s)
        RETURNING id, title, description, completed, created_at, updated_at
    """
    with contextlib.closing(_connect()) as conn:
        with conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (title, description, completed))
            row = cur.fetchone()
            return dict(row)


# PUBLIC_INTERFACE
def update_todo(
    todo_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    completed: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update fields on an existing todo. Only provided fields will be updated.

    Args:
        todo_id: Identifier of the todo.
        title: Optional new title.
        description: Optional new description.
        completed: Optional new completed flag.

    Returns:
        The updated row as dict, or None if the todo does not exist.
    """
    fields: List[str] = []
    params: List[Any] = []

    if title is not None:
        fields.append("title = %s")
        params.append(title)
    if description is not None:
        fields.append("description = %s")
        params.append(description)
    if completed is not None:
        fields.append("completed = %s")
        params.append(completed)

    if not fields:
        # Nothing to update; return current row if exists
        return query_todo_by_id(todo_id)

    params.append(todo_id)
    sql = f"""
        UPDATE todos
        SET {', '.join(fields)}
        WHERE id = %s
        RETURNING id, title, description, completed, created_at, updated_at
    """
    with contextlib.closing(_connect()) as conn:
        with conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
            return dict(row) if row else None


# PUBLIC_INTERFACE
def delete_todo(todo_id: int) -> bool:
    """
    Delete a todo by id.

    Args:
        todo_id: Identifier to delete.

    Returns:
        True if a row was deleted, False otherwise.
    """
    sql = "DELETE FROM todos WHERE id = %s"
    with contextlib.closing(_connect()) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(sql, (todo_id,))
            return cur.rowcount > 0
