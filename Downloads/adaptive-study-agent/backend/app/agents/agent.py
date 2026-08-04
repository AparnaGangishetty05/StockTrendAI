from dataclasses import dataclass
from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app.models.study_models import DailyTask, Progress, StudyPlan, User
from app.services.gemini_service import generate_explanation
from app.tools.planner_tools import create_plan, load_progress, replan_schedule, save_progress


@dataclass
class AgentResult:
    explanation: str
    tasks: List[DailyTask]
    plan_exists: bool


class AdaptiveStudyAgent:
    def __init__(self, db: Session):
        self.db = db

    def run(self, user_id: int) -> AgentResult:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        plan = self.db.query(StudyPlan).filter(StudyPlan.user_id == user_id, StudyPlan.is_active.is_(True)).order_by(StudyPlan.created_at.desc()).first()
        progress = load_progress(user_id, self.db)

        if not plan:
            plan = create_plan(user_id, date.today(), "DBMS, Networks, Operating Systems", 3, self.db)
            tasks = self.db.query(DailyTask).filter(DailyTask.plan_id == plan.id).all()
            explanation = generate_explanation(
                f"Create a concise explanation for a student who has no existing study plan. Mention today's tasks."
            )
            return AgentResult(explanation=explanation, tasks=tasks, plan_exists=True)

        pending_tasks = self.db.query(DailyTask).filter(DailyTask.plan_id == plan.id).all()
        remaining = [task for task in pending_tasks if not task.completed]

        if not remaining:
            explanation = generate_explanation("The student has completed all current tasks; explain that the agent is keeping the plan steady.")
            return AgentResult(explanation=explanation, tasks=pending_tasks, plan_exists=True)

        behind = len(progress) < 2
        if behind:
            replan_schedule(plan.id, self.db)
            tasks = self.db.query(DailyTask).filter(DailyTask.plan_id == plan.id).all()
            explanation = generate_explanation(
                "The student missed previous study sessions, so the agent should explain that it moved the remaining work forward while preserving revision time."
            )
            return AgentResult(explanation=explanation, tasks=tasks, plan_exists=True)

        explanation = generate_explanation("The student is on track; explain that the agent is continuing the existing plan for today.")
        return AgentResult(explanation=explanation, tasks=remaining, plan_exists=True)

    def save_completed(self, user_id: int, tasks: list[dict]) -> None:
        save_progress(user_id, tasks, self.db)
