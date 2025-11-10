from typing import List, Optional

from fastapi import FastAPI, HTTPException, Path, status
from fastapi.middleware.cors import CORSMiddleware

from src.api import db
from src.api.models import TodoCreate, TodoOut, TodoUpdate

app = FastAPI(
    title="Todo API",
    description="FastAPI backend for a simple Todo application with PostgreSQL.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "todos", "description": "CRUD operations for todos"},
    ],
)

# Track database availability for diagnostics
_db_ready: bool = False
_db_error: Optional[str] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict allowed origins.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    Initialize database schema on startup.
    This is wrapped in a try/except so the service can start and expose diagnostics
    even if the database is unavailable at boot time.
    """
    global _db_ready, _db_error
    try:
        db.ensure_schema()
        _db_ready = True
        _db_error = None
    except Exception as exc:  # pragma: no cover - defensive startup behavior
        # Do not crash the whole service; record state for health endpoint
        _db_ready = False
        _db_error = "Database initialization failed"
        # Intentionally avoid logging sensitive details


@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """
    Simple health check endpoint.

    Returns:
        JSON with a 'message' key indicating service health and DB readiness flag.
    """
    return {"message": "Healthy", "db_ready": _db_ready}


# PUBLIC_INTERFACE
@app.get(
    "/api/todos",
    response_model=List[TodoOut],
    tags=["todos"],
    summary="List todos",
    description="Retrieve all todos ordered by id ascending.",
)
def list_todos() -> List[TodoOut]:
    """
    List all todos.

    Returns:
        List of TodoOut items.
    """
    try:
        rows = db.query_all_todos()
    except Exception as exc:
        # Surface a consistent error without leaking DB details
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    return [TodoOut(**r) for r in rows]


# PUBLIC_INTERFACE
@app.post(
    "/api/todos",
    response_model=TodoOut,
    status_code=status.HTTP_201_CREATED,
    tags=["todos"],
    summary="Create todo",
    description="Create a new todo with validated title and optional fields.",
)
def create_todo(payload: TodoCreate) -> TodoOut:
    """
    Create a new todo.

    Args:
        payload: TodoCreate model with title (required), description (optional),
                 completed (optional).

    Returns:
        The created TodoOut.
    """
    try:
        created = db.insert_todo(
            title=payload.title.strip(),
            description=(payload.description or ""),
            completed=bool(payload.completed) if payload.completed is not None else False,
        )
    except Exception as exc:
        # Avoid leaking sensitive DB info
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    return TodoOut(**created)


# PUBLIC_INTERFACE
@app.get(
    "/api/todos/{todo_id}",
    response_model=TodoOut,
    tags=["todos"],
    summary="Get todo by id",
    description="Retrieve a specific todo by its id.",
)
def get_todo(
    todo_id: int = Path(..., ge=1, description="Numeric identifier of the todo"),
) -> TodoOut:
    """
    Get a todo by its identifier.

    Args:
        todo_id: Identifier of the todo.

    Returns:
        The TodoOut item.

    Raises:
        HTTPException 404 if not found.
    """
    try:
        row = db.query_todo_by_id(todo_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    return TodoOut(**row)


# PUBLIC_INTERFACE
@app.put(
    "/api/todos/{todo_id}",
    response_model=TodoOut,
    tags=["todos"],
    summary="Replace todo",
    description="Replace an existing todo's fields with provided values.",
)
def replace_todo(
    payload: TodoUpdate,
    todo_id: int = Path(..., ge=1, description="Identifier of the todo"),
) -> TodoOut:
    """
    Replace an existing todo with provided fields. If a field is omitted, it will not be changed.

    Args:
        payload: TodoUpdate with fields to set.
        todo_id: Identifier.

    Returns:
        Updated TodoOut.

    Raises:
        HTTPException 404 if not found.
    """
    try:
        updated = db.update_todo(
            todo_id=todo_id,
            title=payload.title.strip() if payload.title is not None else None,
            description=payload.description if payload.description is not None else None,
            completed=payload.completed if payload.completed is not None else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    return TodoOut(**updated)


# PUBLIC_INTERFACE
@app.patch(
    "/api/todos/{todo_id}",
    response_model=TodoOut,
    tags=["todos"],
    summary="Update todo",
    description="Partially update a todo with provided fields.",
)
def patch_todo(
    payload: TodoUpdate,
    todo_id: int = Path(..., ge=1, description="Identifier of the todo"),
) -> TodoOut:
    """
    Partially update a todo.

    Args:
        payload: TodoUpdate with one or more fields to update.
        todo_id: Identifier.

    Returns:
        Updated TodoOut.

    Raises:
        HTTPException 404 if not found.
    """
    try:
        updated = db.update_todo(
            todo_id=todo_id,
            title=payload.title.strip() if payload.title is not None else None,
            description=payload.description if payload.description is not None else None,
            completed=payload.completed if payload.completed is not None else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    return TodoOut(**updated)


# PUBLIC_INTERFACE
@app.delete(
    "/api/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["todos"],
    summary="Delete todo",
    description="Delete a todo by id. Returns 204 on success.",
)
def delete_todo(
    todo_id: int = Path(..., ge=1, description="Identifier of the todo"),
) -> None:
    """
    Delete a todo by identifier.

    Args:
        todo_id: Identifier of the todo to delete.

    Raises:
        HTTPException 404 if not found.
    """
    try:
        ok = db.delete_todo(todo_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable.") from exc
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found.")
    # 204 No Content
    return None
