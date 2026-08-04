from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str


class UserOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlanCreate(BaseModel):
    exam_date: date
    subjects: str
    hours_per_day: int


class TaskOut(BaseModel):
    id: int
    task_date: date
    subject: str
    topic: str
    completed: bool

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: int
    exam_date: date
    subjects: str
    hours_per_day: int
    is_active: bool
    daily_tasks: List[TaskOut]

    class Config:
        from_attributes = True


class ProgressItem(BaseModel):
    subject: str
    topic: str


class ProgressOut(BaseModel):
    id: int
    task_date: date
    subject: str
    topic: str
    completed: bool

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    explanation: str
    tasks: List[TaskOut]
    plan_exists: bool
