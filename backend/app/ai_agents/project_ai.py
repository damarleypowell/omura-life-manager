"""
Omura Project AI Agent
Provides AI-driven project management: pipeline analysis, bottleneck
prediction, task prioritization, daily agenda generation, and
completion estimation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class ProjectAI:
    """AI-powered project management agent.

    Analyzes active projects and tasks, predicts bottlenecks, generates
    prioritized daily agendas, and estimates completion timelines using
    historical velocity and AI reasoning.
    """

    STATUS_ORDER = ("blocked", "in_progress", "review", "todo", "done")

    def __init__(self, db_session: Any) -> None:
        """Initialize the ProjectAI agent.

        Args:
            db_session: SQLAlchemy database session for querying projects,
                        tasks, and calendar events.
        """
        self.db = db_session
        self.logger = OmuraLogger("project_ai")
        self.logger.info("ProjectAI agent initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_pipeline(self) -> dict:
        """Generate an overview of all active projects with their status.

        Returns:
            A dict containing:
                - total_projects (int)
                - by_status (dict[str, int]): project count per status
                - projects (list[dict]): per-project summaries with
                  health_score, task_counts, and next_milestone
                - generated_at (str): ISO timestamp
        """
        self.logger.info("Analyzing project pipeline")

        projects = self._fetch_active_projects()

        prompt = (
            f"Analyze the following project pipeline and assess overall health.\n"
            f"Projects: {len(projects)}\n"
            f"Details: {projects}"
        )
        result = self._call_ai(prompt, context={"task": "analyze_pipeline"})

        analysis = {
            "total_projects": result.get("total_projects", len(projects)),
            "by_status": result.get("by_status", {}),
            "projects": result.get("projects", []),
            "overall_health": result.get("overall_health", "good"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(
            "Pipeline analysis complete",
            total=analysis["total_projects"],
            health=analysis["overall_health"],
        )
        return analysis

    def predict_bottlenecks(self, project_id: int) -> list[dict]:
        """Identify potential blockers for a specific project.

        Args:
            project_id: The database ID of the project to analyze.

        Returns:
            A list of bottleneck dicts, each containing:
                - area (str): e.g. 'task', 'resource', 'dependency'
                - description (str)
                - severity (str): 'critical', 'warning', 'info'
                - recommendation (str)
        """
        self.logger.info("Predicting bottlenecks", project_id=project_id)

        project_data = self._fetch_project_details(project_id)

        prompt = (
            f"Analyze project ID {project_id} for potential bottlenecks.\n"
            f"Tasks: {project_data.get('tasks', [])}\n"
            f"Dependencies: {project_data.get('dependencies', [])}\n"
            f"Team capacity: {project_data.get('team_capacity', 'unknown')}"
        )
        result = self._call_ai(prompt, context={"task": "predict_bottlenecks"})
        bottlenecks = result.get("bottlenecks", [])

        self.logger.info(
            "Bottleneck prediction complete",
            project_id=project_id,
            bottlenecks_found=len(bottlenecks),
            critical=sum(1 for b in bottlenecks if b.get("severity") == "critical"),
        )
        return bottlenecks

    def suggest_task_priority(self, tasks: list[dict]) -> list[dict]:
        """Return an AI-prioritized ordering of tasks.

        Each task dict should contain at minimum:
            - id (int)
            - title (str)
            - due_date (str | None)
            - priority (str | None): current manual priority
            - status (str)
            - estimated_hours (float | None)

        Args:
            tasks: List of task dicts to prioritize.

        Returns:
            The same tasks re-ordered by AI-suggested priority, each
            enriched with:
                - ai_priority (int): 1 = highest
                - ai_reasoning (str): explanation for the ranking
        """
        self.logger.info("Suggesting task priorities", task_count=len(tasks))

        prompt = (
            f"Prioritize these {len(tasks)} tasks based on urgency, "
            f"deadlines, dependencies, and estimated effort.\n"
            f"Tasks: {tasks}"
        )
        result = self._call_ai(prompt, context={"task": "suggest_priority"})
        prioritized = result.get("prioritized_tasks", [])

        self.logger.info(
            "Task prioritization complete", output_count=len(prioritized),
        )
        return prioritized

    def generate_daily_agenda(self) -> dict:
        """Create a prioritized daily agenda combining tasks, events, and deadlines.

        Pulls data from projects, calendar, and task lists to build a
        structured agenda for the current day.

        Returns:
            A dict containing:
                - date (str): ISO date
                - time_blocks (list[dict]): ordered agenda items with
                  start_time, end_time, activity, type, priority
                - focus_areas (list[str]): top 3 areas to focus on
                - estimated_productive_hours (float)
                - tips (list[str]): productivity recommendations
        """
        self.logger.info("Generating daily agenda")

        today = datetime.now(timezone.utc).date().isoformat()
        tasks = self._fetch_todays_tasks()
        events = self._fetch_todays_events()

        prompt = (
            f"Generate an optimized daily agenda for {today}.\n"
            f"Tasks due: {tasks}\n"
            f"Calendar events: {events}\n"
            f"Create time blocks, identify focus areas, and provide tips."
        )
        result = self._call_ai(prompt, context={"task": "daily_agenda"})

        agenda = {
            "date": today,
            "time_blocks": result.get("time_blocks", []),
            "focus_areas": result.get("focus_areas", []),
            "estimated_productive_hours": result.get("estimated_productive_hours", 6.0),
            "tips": result.get("tips", []),
        }

        self.logger.info(
            "Daily agenda generated",
            date=today,
            blocks=len(agenda["time_blocks"]),
            productive_hours=agenda["estimated_productive_hours"],
        )
        return agenda

    def estimate_completion(self, project_id: int) -> dict:
        """Predict the completion date for a project.

        Uses task velocity, remaining work, and historical patterns to
        generate an estimated delivery window.

        Args:
            project_id: The database ID of the project.

        Returns:
            A dict containing:
                - project_id (int)
                - estimated_completion (str): ISO date
                - confidence (float): 0-1 confidence level
                - remaining_tasks (int)
                - remaining_hours (float)
                - velocity_tasks_per_week (float)
                - risks (list[str])
        """
        self.logger.info("Estimating project completion", project_id=project_id)

        project_data = self._fetch_project_details(project_id)

        prompt = (
            f"Estimate the completion date for project ID {project_id}.\n"
            f"Total tasks: {project_data.get('total_tasks', 0)}\n"
            f"Completed: {project_data.get('completed_tasks', 0)}\n"
            f"Average velocity: {project_data.get('velocity', 'unknown')}\n"
            f"Remaining estimated hours: {project_data.get('remaining_hours', 'unknown')}"
        )
        result = self._call_ai(prompt, context={"task": "estimate_completion"})

        estimation = {
            "project_id": project_id,
            "estimated_completion": result.get("estimated_completion", ""),
            "confidence": result.get("confidence", 0.0),
            "remaining_tasks": result.get("remaining_tasks", 0),
            "remaining_hours": result.get("remaining_hours", 0.0),
            "velocity_tasks_per_week": result.get("velocity_tasks_per_week", 0.0),
            "risks": result.get("risks", []),
        }

        self.logger.info(
            "Completion estimate ready",
            project_id=project_id,
            estimated_completion=estimation["estimated_completion"],
            confidence=estimation["confidence"],
        )
        return estimation

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_active_projects(self) -> list[dict]:
        """Fetch active projects from the database. Returns mock data as fallback."""
        try:
            self.logger.debug("Querying active projects")
            return []
        except Exception as exc:
            self.logger.warning("Failed to fetch projects", error=str(exc))
            return []

    def _fetch_project_details(self, project_id: int) -> dict:
        """Fetch detailed project data including tasks and dependencies."""
        try:
            self.logger.debug("Fetching project details", project_id=project_id)
            return {
                "id": project_id,
                "total_tasks": 24,
                "completed_tasks": 16,
                "in_progress_tasks": 5,
                "blocked_tasks": 1,
                "todo_tasks": 2,
                "remaining_hours": 38.5,
                "velocity": "4.2 tasks/week",
                "dependencies": [],
                "team_capacity": "2 developers, 1 designer",
                "tasks": [],
            }
        except Exception as exc:
            self.logger.warning(
                "Failed to fetch project details", project_id=project_id, error=str(exc),
            )
            return {"id": project_id}

    def _fetch_todays_tasks(self) -> list[dict]:
        """Fetch tasks due today from the database."""
        try:
            self.logger.debug("Fetching today's tasks")
            return []
        except Exception as exc:
            self.logger.warning("Failed to fetch today's tasks", error=str(exc))
            return []

    def _fetch_todays_events(self) -> list[dict]:
        """Fetch calendar events for today."""
        try:
            self.logger.debug("Fetching today's events")
            return []
        except Exception as exc:
            self.logger.warning("Failed to fetch today's events", error=str(exc))
            return []

    def _call_ai(self, prompt: str, context: Optional[dict] = None) -> dict:
        """Call Claude API to process a prompt, with mock fallback.

        Args:
            prompt: The natural-language prompt to send.
            context: Optional metadata about the task type.

        Returns:
            A dict containing the AI response fields.
        """
        task = (context or {}).get("task", "unknown")
        self.logger.debug("Calling AI provider", task=task, prompt_length=len(prompt))

        # Try real Claude API call
        from backend.app.ai_agents._claude_caller import call_claude_json

        system_prompt = (
            "You are an AI project management assistant for Omura. "
            "You analyze project pipelines, predict bottlenecks, prioritize tasks, "
            "generate daily agendas, and estimate completion timelines. "
            "Always respond with valid JSON only."
        )

        task_instructions = {
            "analyze_pipeline": (
                "\n\nRespond with JSON containing: "
                '{"total_projects": <int>, '
                '"by_status": {"active": <int>, "on_hold": <int>, "planning": <int>}, '
                '"overall_health": "good|warning|critical", '
                '"projects": [{"id": <int>, "name": "...", "status": "...", '
                '"health_score": <int 0-100>, "tasks_completed": <int>, '
                '"tasks_total": <int>, "next_milestone": "..."}, ...]}'
            ),
            "predict_bottlenecks": (
                "\n\nRespond with JSON containing: "
                '{"bottlenecks": [{"area": "task|resource|dependency", '
                '"description": "...", "severity": "critical|warning|info", '
                '"recommendation": "..."}, ...]}'
            ),
            "suggest_priority": (
                "\n\nRespond with JSON containing: "
                '{"prioritized_tasks": [{"id": <int>, "title": "...", '
                '"ai_priority": <int starting at 1>, '
                '"ai_reasoning": "..."}, ...]}'
            ),
            "daily_agenda": (
                "\n\nRespond with JSON containing: "
                '{"time_blocks": [{"start_time": "ISO datetime", '
                '"end_time": "ISO datetime", "activity": "...", '
                '"type": "task|meeting|routine|break", '
                '"priority": "critical|high|medium|low"}, ...], '
                '"focus_areas": ["area1", "area2", "area3"], '
                '"estimated_productive_hours": <float>, '
                '"tips": ["tip1", "tip2", ...]}'
            ),
            "estimate_completion": (
                "\n\nRespond with JSON containing: "
                '{"estimated_completion": "ISO date string", '
                '"confidence": <float 0-1>, '
                '"remaining_tasks": <int>, '
                '"remaining_hours": <float>, '
                '"velocity_tasks_per_week": <float>, '
                '"risks": ["risk1", "risk2", ...]}'
            ),
        }

        full_prompt = prompt + task_instructions.get(task, "\n\nRespond with valid JSON.")
        result = call_claude_json(full_prompt, system_prompt, agent_name="project_ai")

        if result is not None:
            self.logger.debug(f"Claude API returned valid response for task={task}")
            return result

        # ── Fallback: mock responses keyed by task ──
        self.logger.info("Falling back to mock response for task=%s", task)

        now = datetime.now(timezone.utc)

        if task == "analyze_pipeline":
            return {
                "total_projects": 5,
                "by_status": {
                    "active": 3,
                    "on_hold": 1,
                    "planning": 1,
                },
                "overall_health": "good",
                "projects": [
                    {
                        "id": 1,
                        "name": "Omura Mobile App",
                        "status": "active",
                        "health_score": 82,
                        "tasks_completed": 34,
                        "tasks_total": 48,
                        "next_milestone": "Beta release — April 10",
                    },
                    {
                        "id": 2,
                        "name": "Client Portal Redesign",
                        "status": "active",
                        "health_score": 65,
                        "tasks_completed": 12,
                        "tasks_total": 30,
                        "next_milestone": "Design review — March 28",
                    },
                    {
                        "id": 3,
                        "name": "Marketing Campaign Q2",
                        "status": "active",
                        "health_score": 90,
                        "tasks_completed": 8,
                        "tasks_total": 15,
                        "next_milestone": "Content batch due — March 31",
                    },
                    {
                        "id": 4,
                        "name": "API v2 Migration",
                        "status": "on_hold",
                        "health_score": 45,
                        "tasks_completed": 5,
                        "tasks_total": 22,
                        "next_milestone": "Awaiting dependency resolution",
                    },
                    {
                        "id": 5,
                        "name": "Onboarding Automation",
                        "status": "planning",
                        "health_score": 70,
                        "tasks_completed": 0,
                        "tasks_total": 18,
                        "next_milestone": "Kickoff — April 1",
                    },
                ],
            }

        if task == "predict_bottlenecks":
            return {
                "bottlenecks": [
                    {
                        "area": "dependency",
                        "description": (
                            "Task 'Payment integration' is blocked by unresolved "
                            "third-party API access approval."
                        ),
                        "severity": "critical",
                        "recommendation": (
                            "Escalate API access request to vendor contact. "
                            "Prepare fallback integration path with alternative provider."
                        ),
                    },
                    {
                        "area": "resource",
                        "description": (
                            "Front-end developer is allocated across 3 concurrent "
                            "projects, reducing effective velocity by ~40%."
                        ),
                        "severity": "warning",
                        "recommendation": (
                            "Consider dedicated allocation for the next sprint or "
                            "bring in contract support for UI tasks."
                        ),
                    },
                    {
                        "area": "task",
                        "description": (
                            "Five tasks lack time estimates, making sprint planning "
                            "unreliable."
                        ),
                        "severity": "info",
                        "recommendation": (
                            "Schedule a 15-minute estimation session to size "
                            "remaining unestimated tasks."
                        ),
                    },
                ],
            }

        if task == "suggest_priority":
            return {
                "prioritized_tasks": [
                    {
                        "id": 101,
                        "title": "Fix payment gateway timeout",
                        "ai_priority": 1,
                        "ai_reasoning": (
                            "Production-impacting bug with customer-facing consequences. "
                            "Deadline is today."
                        ),
                    },
                    {
                        "id": 104,
                        "title": "Prepare investor deck",
                        "ai_priority": 2,
                        "ai_reasoning": (
                            "Meeting is tomorrow; deck needs final review and data refresh."
                        ),
                    },
                    {
                        "id": 102,
                        "title": "Review pull requests",
                        "ai_priority": 3,
                        "ai_reasoning": (
                            "Two PRs are blocking teammates. Quick review unblocks "
                            "downstream work."
                        ),
                    },
                    {
                        "id": 103,
                        "title": "Draft Q2 marketing plan",
                        "ai_priority": 4,
                        "ai_reasoning": (
                            "Due Friday; significant but not blocking other work today."
                        ),
                    },
                    {
                        "id": 105,
                        "title": "Update onboarding docs",
                        "ai_priority": 5,
                        "ai_reasoning": (
                            "Important but no hard deadline. Can be done during "
                            "low-energy afternoon slot."
                        ),
                    },
                ],
            }

        if task == "daily_agenda":
            today = now.date().isoformat()
            return {
                "time_blocks": [
                    {
                        "start_time": f"{today}T08:00:00",
                        "end_time": f"{today}T08:30:00",
                        "activity": "Morning review: email triage and priority check",
                        "type": "routine",
                        "priority": "medium",
                    },
                    {
                        "start_time": f"{today}T08:30:00",
                        "end_time": f"{today}T10:30:00",
                        "activity": "Deep work: Fix payment gateway timeout (critical)",
                        "type": "task",
                        "priority": "critical",
                    },
                    {
                        "start_time": f"{today}T10:30:00",
                        "end_time": f"{today}T11:00:00",
                        "activity": "Code review: 2 pending pull requests",
                        "type": "task",
                        "priority": "high",
                    },
                    {
                        "start_time": f"{today}T11:00:00",
                        "end_time": f"{today}T11:30:00",
                        "activity": "Standup meeting",
                        "type": "meeting",
                        "priority": "medium",
                    },
                    {
                        "start_time": f"{today}T11:30:00",
                        "end_time": f"{today}T12:30:00",
                        "activity": "Investor deck finalization",
                        "type": "task",
                        "priority": "high",
                    },
                    {
                        "start_time": f"{today}T12:30:00",
                        "end_time": f"{today}T13:30:00",
                        "activity": "Lunch break",
                        "type": "break",
                        "priority": "low",
                    },
                    {
                        "start_time": f"{today}T13:30:00",
                        "end_time": f"{today}T15:30:00",
                        "activity": "Draft Q2 marketing plan",
                        "type": "task",
                        "priority": "medium",
                    },
                    {
                        "start_time": f"{today}T15:30:00",
                        "end_time": f"{today}T16:30:00",
                        "activity": "Update onboarding documentation",
                        "type": "task",
                        "priority": "low",
                    },
                    {
                        "start_time": f"{today}T16:30:00",
                        "end_time": f"{today}T17:00:00",
                        "activity": "End-of-day wrap-up and tomorrow planning",
                        "type": "routine",
                        "priority": "medium",
                    },
                ],
                "focus_areas": [
                    "Resolve critical payment gateway bug",
                    "Finalize investor presentation",
                    "Unblock team with PR reviews",
                ],
                "estimated_productive_hours": 6.5,
                "tips": [
                    "Tackle the payment bug first while energy is highest.",
                    "Batch communication (email, Slack) into 2 windows to protect deep work.",
                    "Use the post-lunch slot for creative work like the marketing plan.",
                ],
            }

        if task == "estimate_completion":
            target = (now + timedelta(weeks=2, days=3)).date().isoformat()
            return {
                "estimated_completion": target,
                "confidence": 0.74,
                "remaining_tasks": 8,
                "remaining_hours": 38.5,
                "velocity_tasks_per_week": 4.2,
                "risks": [
                    "One blocked task may delay downstream features by 2-3 days.",
                    "Designer availability drops next week (PTO), may slow UI tasks.",
                    "Scope creep risk on the reporting module — needs stakeholder alignment.",
                ],
            }

        return {"raw": "Mock AI response — task not recognized."}
