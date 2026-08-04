# Adaptive Study Planner Agent

## Architecture

This project combines a React + Tailwind frontend with a FastAPI backend and a LangGraph-based agent workflow. The backend stores user, plan, task, and progress information in SQLite through SQLAlchemy.

## Workflow

The single agent follows a simple but genuine agentic loop:

1. Load prior progress from SQLite.
2. Decide whether a plan already exists.
3. If no plan exists, create one.
4. If the student is behind, replan the schedule.
5. Otherwise continue with the existing plan.
6. Return a short explanation and the tasks for today.

## Tools

The agent uses four tools conceptually:
- create_plan
- load_progress
- save_progress
- replan_schedule

## Memory

The application uses SQLite as persistent memory for study plans and historical progress. This gives the agent a simple long-term context across sessions.

## Why this is agentic AI

This is agentic because the system makes decisions based on state, selects actions, and adapts its behavior. It is not just a static prompt; it uses a workflow with tool-like operations and persistent memory to choose the next best move.

## Run locally

### Backend

```bash
cd backend
pip install -r requirements.txt
python run.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173.
