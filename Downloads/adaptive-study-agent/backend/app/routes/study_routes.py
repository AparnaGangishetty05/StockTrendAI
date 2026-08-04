from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.agent import AdaptiveStudyAgent
from app.database.connection import get_db
from app.models.study_models import DailyTask, Progress, StudyPlan, User
from app.schemas import DashboardResponse, PlanCreate, PlanOut, ProgressItem, ProgressOut, TaskOut, UserCreate, UserOut

router = APIRouter(prefix="/api", tags=["study"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/plans", response_model=PlanOut)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(name="Demo Student")
        db.add(user)
        db.commit()
        db.refresh(user)

    plan = StudyPlan(
        user_id=user.id,
        exam_date=payload.exam_date,
        subjects=payload.subjects,
        hours_per_day=payload.hours_per_day,
        is_active=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    tasks = []
    for index, subject in enumerate([item.strip() for item in payload.subjects.split(",") if item.strip()]):
        task = DailyTask(
            plan_id=plan.id,
            task_date=date.today() + __import__("datetime").timedelta(days=index % 3),
            subject=subject,
            topic=f"{subject} core review",
            completed=False,
        )
        db.add(task)
        tasks.append(task)
    db.commit()
    plan.daily_tasks = tasks
    return plan


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(name="Demo Student")
        db.add(user)
        db.commit()
        db.refresh(user)

    agent = AdaptiveStudyAgent(db)
    result = agent.run(user.id)
    tasks = [
        TaskOut(
            id=task.id,
            task_date=task.task_date,
            subject=task.subject,
            topic=task.topic,
            completed=task.completed,
        )
        for task in result.tasks
    ]
    return DashboardResponse(explanation=result.explanation, tasks=tasks, plan_exists=result.plan_exists)


@router.post("/progress")
def save_progress(payload: list[ProgressItem], db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        return {"status": "ok"}

    agent = AdaptiveStudyAgent(db)
    agent.save_completed(user.id, [{"subject": item.subject, "topic": item.topic} for item in payload])
    return {"status": "saved"}


@router.get("/progress", response_model=list[ProgressOut])
def get_progress(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        return []
    return db.query(Progress).filter(Progress.user_id == user.id).all()
