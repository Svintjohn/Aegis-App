"""
Aegis data models.

Mirrors the two "things" the app needs to remember, straight from the
proposal:
  Thing 1: Projects/Contracts — client ID, freelancer ID, submission
           link, 14-day timer status. Extended with milestones.
  Thing 2: User Finances — USDC balance, linked GCash/Maya details.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MilestoneStatus(str, Enum):
    pending = "pending"
    locked = "locked"
    submitted = "submitted"
    releasing = "releasing"   
    released = "released"
    disputed = "disputed"


class Milestone(BaseModel):
    id: str
    label: str
    amount_php: float
    status: MilestoneStatus = MilestoneStatus.pending
    due_date: Optional[datetime] = None


class ProjectStatus(str, Enum):
    awaiting_deposit = "awaiting_deposit"
    locked = "locked"
    in_progress = "in_progress"
    disputed = "disputed"
    completed = "completed"


class Project(BaseModel):
    id: str
    title: str
    client_id: str
    freelancer_id: str
    submission_link: Optional[str] = None
    total_php: float
    status: ProjectStatus = ProjectStatus.awaiting_deposit
    milestones: list[Milestone] = Field(default_factory=list)

    # Anti-ghosting timer — core MVP feature #2.
    ghost_timer_started_at: Optional[datetime] = None
    ghost_timer_duration_days: int = 14

    @property
    def ghost_timer_expires_at(self) -> Optional[datetime]:
        if self.ghost_timer_started_at is None:
            return None
        return self.ghost_timer_started_at + timedelta(days=self.ghost_timer_duration_days)

    @property
    def ghost_timer_expired(self) -> bool:
        exp = self.ghost_timer_expires_at
        return exp is not None and datetime.utcnow() >= exp


class ProjectCreate(BaseModel):
    title: str
    client_id: str
    freelancer_id: str
    milestones: list[Milestone]


class Wallet(BaseModel):
    user_id: str
    usdc_balance: float = 0.0
    linked_cash_app: Optional[str] = None   
    linked_account_last4: Optional[str] = None


class OffRampRequest(BaseModel):
    user_id: str
    amount_usdc: float
