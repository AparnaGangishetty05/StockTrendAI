from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.study_models import DailyTask, Progress, StudyPlan, User


def create_plan(user_id: int, exam_date: date, subjects: str, hours_per_day: int, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    plan = StudyPlan(
        user_id=user_id,
        exam_date=exam_date,
        subjects=subjects,
        hours_per_day=hours_per_day,
        is_active=True,
    )
    db.add(plan)
    db.flush()

    subject_list = [item.strip() for item in subjects.split(",") if item.strip()]
    for index, subject in enumerate(subject_list):
        task_date = date.today() + timedelta(days=index % 3)
        task = DailyTask(
            plan_id=plan.id,
            task_date=task_date,
            subject=subject,
            topic=f"{subject} core review",
            completed=False,
        )
        db.add(task)

    db.commit()
    return plan


def load_progress(user_id: int, db: Session):
    return db.query(Progress).filter(Progress.user_id == user_id).all()


def save_progress(user_id: int, tasks: list[dict], db: Session):
    for task in tasks:
        entry = Progress(
            user_id=user_id,
            task_date=date.today(),
            subject=task["subject"],
            topic=task["topic"],
            completed=True,
        )
        db.add(entry)
    db.commit()
    return True


def replan_schedule(plan_id: int, db: Session):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise ValueError("Plan not found")

    tasks = db.query(DailyTask).filter(DailyTask.plan_id == plan_id).all()
    for task in tasks:
        if task.task_date < date.today():
            task.completed = False
    db.commit()
    return tasks
