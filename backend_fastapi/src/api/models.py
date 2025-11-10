from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TodoBase(BaseModel):
    """
    Base schema containing common todo fields.
    """
    title: str = Field(..., min_length=1, max_length=200, description="Todo title (1..200 chars).")
    description: Optional[str] = Field(default="", description="Optional detailed description.")
    completed: Optional[bool] = Field(default=False, description="Completion status.")


class TodoCreate(TodoBase):
    """
    Schema for creating a todo. All TodoBase fields are accepted;
    completed is optional and defaults to False.
    """

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        # Trim and ensure non-empty after trimming.
        vt = v.strip()
        if not vt:
            raise ValueError("Title cannot be empty or whitespace.")
        return vt


class TodoUpdate(BaseModel):
    """
    Schema for updating a todo. All fields are optional and only provided
    fields will be updated.
    """
    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="New title.")
    description: Optional[str] = Field(default=None, description="New description.")
    completed: Optional[bool] = Field(default=None, description="New completion status.")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        vt = v.strip()
        if not vt:
            raise ValueError("Title cannot be empty or whitespace.")
        return vt


class TodoOut(BaseModel):
    """
    Response schema representing a todo stored in the database.
    """
    id: int = Field(..., description="Unique identifier")
    title: str = Field(..., description="Title")
    description: str = Field(..., description="Description")
    completed: bool = Field(..., description="Completion status")
    created_at: str = Field(..., description="Creation timestamp in ISO format")
    updated_at: str = Field(..., description="Update timestamp in ISO format")
