"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional


class Preferences(BaseModel):
    """User preferences for automatic schedule generation."""
    wake_time: str = Field(default="07:00", pattern=r"^\d{2}:\d{2}$")
    sleep_time: str = Field(default="23:00", pattern=r"^\d{2}:\d{2}$")
    work_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    work_end: str = Field(default="17:00", pattern=r"^\d{2}:\d{2}$")
    breakfast_duration: int = Field(default=30, ge=15, le=120)
    lunch_duration: int = Field(default=60, ge=15, le=120)
    dinner_duration: int = Field(default=45, ge=15, le=120)
    exercise_enabled: bool = True
    exercise_duration: int = Field(default=60, ge=15, le=180)
    study_enabled: bool = True
    study_duration: int = Field(default=90, ge=15, le=300)


class ScheduleBlock(BaseModel):
    """A single time block in the daily schedule."""
    id: Optional[int] = None
    schedule_date: str
    start_time: str
    end_time: str
    title: str
    category: str = Field(
        ...,
        pattern=r"^(sleep|work|meal|exercise|study|personal|free|routine)$"
    )
    description: str = ""
    is_fixed: bool = False
    sort_order: int = 0


class ScheduleBlockCreate(BaseModel):
    """Schema for creating a new block."""
    schedule_date: str
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    title: str = Field(..., min_length=1, max_length=100)
    category: str = Field(
        default="personal",
        pattern=r"^(sleep|work|meal|exercise|study|personal|free|routine)$"
    )
    description: str = ""


class ScheduleBlockUpdate(BaseModel):
    """Schema for updating an existing block."""
    start_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(
        default=None,
        pattern=r"^(sleep|work|meal|exercise|study|personal|free|routine)$"
    )
    description: Optional[str] = None


class AgentChatRequest(BaseModel):
    """Schema for chatting with the AI agent."""
    message: str = Field(..., min_length=1)
    target_date: Optional[str] = None

