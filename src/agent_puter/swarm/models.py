"""
models.py — Shared Pydantic data models for the agent swarm.

These are the typed "contracts" that flow between agents via A2A.
All inter-agent messages MUST be representable as one of these models.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    """Lifecycle states for a single agent-executed task."""
    PENDING = "pending"       # Queued, not yet assigned
    IN_PROGRESS = "in_progress"  # Assigned agent is working
    REVIEW = "review"         # Awaiting QA review
    DONE = "done"             # QA passed
    FAILED = "failed"         # QA retries exhausted


class ProjectStatus(str, Enum):
    """High-level lifecycle phases for a consulting project."""
    INTAKE = "intake"         # Session received, not yet briefed
    PLANNING = "planning"     # Sales → CEO → PM decomposing the brief
    EXECUTION = "execution"   # Engineers and researchers building
    QA = "qa"                 # QA review cycle in progress
    DELIVERED = "delivered"   # All tasks done, CEO approved
    CANCELLED = "cancelled"   # Manually cancelled or abandoned


# ---------------------------------------------------------------------------
# Core business objects
# ---------------------------------------------------------------------------


class Task(BaseModel):
    """
    A single unit of work assigned to one execution agent.

    The agency loop creates Task objects during the PM decomposition phase.
    Each task is dispatched to an agent (engineer / researcher) via A2A,
    then reviewed by the QA agent. Retries are tracked here.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    assigned_to: Optional[str] = None          # agent role name (e.g. "engineer")
    status: TaskStatus = TaskStatus.PENDING
    output: Optional[str] = None               # text produced by the execution agent
    qa_feedback: Optional[str] = None          # QA reviewer's comments on last attempt
    retry_count: int = 0                       # incremented each time QA fails
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Proposal(BaseModel):
    """Formal proposal presented to the client before deposit payment."""
    problem_statement: str = ""
    solution_overview: str = ""
    implementation_plan: str = ""
    deliverables: list[str] = Field(default_factory=list)
    estimated_hours: int = 0
    delivery_eta_days: int = 0
    total_price_usd: float = 0.0
    deposit_amount_usd: float = 0.0   # 20%
    final_amount_usd: float = 0.0     # 80%
    payment_structure: str = (
        "20% non-refundable deposit required before work begins. "
        "Remaining 80% due after demo review and before full delivery."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    client_id: str
    status: ProjectStatus = ProjectStatus.INTAKE
    tasks: list[Task] = Field(default_factory=list)
    budget_tokens: int = 100_000
    tokens_used: int = 0
    # --- payment & proposal fields ---
    proposal: Optional[Proposal] = None
    total_price_usd: float = 0.0
    deposit_paid: bool = False
    final_paid: bool = False
    demo_url: Optional[str] = None
    stripe_deposit_intent_id: Optional[str] = None
    stripe_final_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Consultation session (client chat with Sales Agent)
# ---------------------------------------------------------------------------


class ConsultMessage(BaseModel):
    """A single turn in a consultation transcript."""
    role: str                               # "user" | "agent"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConsultSession(BaseModel):
    """
    A live chat session between a client and the Sales Agent.

    Created by POST /api/consult/start.  Completed by POST /api/consult/{id}/complete,
    which triggers the agency loop and populates project_id.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    client_email: str
    messages: list[ConsultMessage] = Field(default_factory=list)
    project_id: Optional[str] = None       # set after handle_client_request completes
    status: str = "active"                 # "active" | "complete"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# A2A message envelopes
# ---------------------------------------------------------------------------


class ClientRequest(BaseModel):
    """Inbound request from an external client / user."""
    client_id: str
    request_text: str
    budget_hint: Optional[int] = None


class AgentMessage(BaseModel):
    """Generic envelope for agent-to-agent communication."""
    sender: str
    recipient: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReviewResult(BaseModel):
    """Decision returned by the QA agent."""
    task_id: str
    passed: bool
    feedback: str
    reviewer: str = "qa_agent"


# ---------------------------------------------------------------------------
# Dependency container
# ---------------------------------------------------------------------------


class AgencyDeps(BaseModel):
    """
    Runtime dependency container.  Holds in-memory state and config.
    In production this would be backed by the Puter KV store.
    """
    model_config = {"arbitrary_types_allowed": True}

    puter_token: Optional[str] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    projects: dict[str, Project] = Field(default_factory=dict)
    sessions: dict[str, ConsultSession] = Field(default_factory=dict)
    max_qa_retries: int = 5
