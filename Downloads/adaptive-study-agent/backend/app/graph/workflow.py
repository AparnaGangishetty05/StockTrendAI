from typing import TypedDict

from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    user_id: int
    explanation: str
    tasks: list
    plan_exists: bool


def build_workflow():
    workflow = StateGraph(AgentState)

    def run_agent_node(state: AgentState):
        from app.agents.agent import AdaptiveStudyAgent
        from app.database.connection import SessionLocal

        db = SessionLocal()
        try:
            agent = AdaptiveStudyAgent(db)
            result = agent.run(state["user_id"])
            return {
                "user_id": state["user_id"],
                "explanation": result.explanation,
                "tasks": result.tasks,
                "plan_exists": result.plan_exists,
            }
        finally:
            db.close()

    workflow.add_node("agent", run_agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    return workflow.compile()
