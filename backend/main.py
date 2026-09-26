"""
Aegis backend — FastAPI reference implementation.

Covers the three MVP features from the proposal:
  1. "Money Locked" Dashboard   -> GET /projects/{id}
  2. Anti-Ghosting Timer        -> POST /milestones/{id}/submit,
                                   background sweep in check_ghost_timers()
  3. Instant Off-Ramping        -> POST /wallet/offramp

NOTE: this is an in-memory reference implementation meant to be swapped
for a real DB (Postgres) and a real smart-contract client (web3.py /
solana-py depending on chain choice) before production. The escrow
release itself should ultimately be a signed on-chain transaction, not
just a status flip in a database — this code marks exactly where that
call belongs (`_release_escrow_onchain`).
"""
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid

from models import (
    Project, ProjectCreate, ProjectStatus,
    Milestone, MilestoneStatus,
    Wallet, OffRampRequest,
)

app = FastAPI(title="Aegis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECTS: dict[str, Project] = {}
WALLETS: dict[str, Wallet] = {}


def _release_escrow_onchain(project: Project, milestone: Milestone) -> None:
    """
    Placeholder for the real smart-contract call that moves locked
    USDC to the freelancer's wallet address. This is the piece the
    proposal flags as the single biggest risk ("Building a reliable
    backend that perfectly syncs with local crypto-exchanges").
    Wire this to web3.py/solana-py + the escrow contract's release()
    method, then credit WALLETS[freelancer_id] once the tx confirms.
    """
    wallet = WALLETS.setdefault(project.freelancer_id, Wallet(user_id=project.freelancer_id))
    wallet.usdc_balance += milestone.amount_php / 58.0  # mock PHP->USDC rate


@app.get("/")
def root():
    return {"status": "ok", "service": "Aegis API", "docs": "/docs"}


@app.post("/projects", response_model=Project)
def create_project(payload: ProjectCreate):
    project = Project(
        id=str(uuid.uuid4()),
        title=payload.title,
        client_id=payload.client_id,
        freelancer_id=payload.freelancer_id,
        total_php=sum(m.amount_php for m in payload.milestones),
        milestones=payload.milestones,
        status=ProjectStatus.awaiting_deposit,
    )
    PROJECTS[project.id] = project
    return project


@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.post("/projects/{project_id}/fund", response_model=Project)
def fund_project(project_id: str):
    """Client deposits funds -> Trust Lock engaged. Feature #1."""
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for m in project.milestones:
        m.status = MilestoneStatus.locked
    project.status = ProjectStatus.locked
    return project


@app.post("/milestones/{project_id}/{milestone_id}/submit", response_model=Project)
def submit_milestone(project_id: str, milestone_id: str):
    """Freelancer submits work -> starts the 14-day anti-ghosting timer."""
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for m in project.milestones:
        if m.id == milestone_id:
            m.status = MilestoneStatus.releasing
    project.ghost_timer_started_at = datetime.utcnow()
    project.status = ProjectStatus.in_progress
    return project


@app.post("/milestones/{project_id}/{milestone_id}/approve", response_model=Project)
def approve_milestone(project_id: str, milestone_id: str):
    """Client approves -> immediate release, no need to wait out the timer."""
    project = PROJECTS.get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for m in project.milestones:
        if m.id == milestone_id:
            m.status = MilestoneStatus.released
            _release_escrow_onchain(project, m)
    if all(m.status == MilestoneStatus.released for m in project.milestones):
        project.status = ProjectStatus.completed
        project.ghost_timer_started_at = None
    return project


@app.post("/system/check-ghost-timers")
def check_ghost_timers():
    """
    Feature #2, the referee. Intended to run on a schedule (cron /
    Celery beat / cloud scheduler) — sweeps every project and
    auto-releases any milestone whose client has gone silent past
    the 14-day window, exactly as the proposal specifies.
    """
    released = []
    for project in PROJECTS.values():
        if project.ghost_timer_expired:
            for m in project.milestones:
                if m.status == MilestoneStatus.releasing:
                    m.status = MilestoneStatus.released
                    _release_escrow_onchain(project, m)
                    released.append((project.id, m.id))
            project.ghost_timer_started_at = None
    return {"auto_released": released}


@app.get("/wallet/{user_id}", response_model=Wallet)
def get_wallet(user_id: str):
    return WALLETS.setdefault(user_id, Wallet(user_id=user_id))


@app.post("/wallet/offramp")
def offramp(payload: OffRampRequest):
    """Feature #3 — swap USDC to PHP and push to GCash/Maya."""
    wallet = WALLETS.setdefault(payload.user_id, Wallet(user_id=payload.user_id))
    if payload.amount_usdc > wallet.usdc_balance:
        raise HTTPException(400, "Insufficient balance")
    wallet.usdc_balance -= payload.amount_usdc
    php_amount = payload.amount_usdc * 58.0  # mock rate — call Coins.ph/Maya API here
    return {
        "status": "sent",
        "php_amount": round(php_amount, 2),
        "destination": f"{wallet.linked_cash_app or 'GCash'} •••• {wallet.linked_account_last4 or '0000'}",
    }
