"""Support API — ticket CRUD and feedback summaries."""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, SupportTicket, UserFeedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("/tickets")
async def list_tickets(
    status: str | None = Query(None, regex="^(open|in_progress|resolved|closed)$"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """List support tickets, optionally filtered by status."""
    query = select(SupportTicket).order_by(desc(SupportTicket.created_at)).limit(limit)
    if status:
        query = query.where(SupportTicket.status == status)
    result = await session.execute(query)
    tickets = result.scalars().all()

    return [
        {
            "id": t.id,
            "telegram_id": t.telegram_id,
            "username": t.username,
            "category": t.category,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        }
        for t in tickets
    ]


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: int, session: AsyncSession = Depends(get_session)):
    """Get a specific support ticket."""
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {
        "id": t.id,
        "telegram_id": t.telegram_id,
        "username": t.username,
        "category": t.category,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "admin_notes": t.admin_notes,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
    }


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    new_status: str = Query(..., regex="^(open|in_progress|resolved|closed)$"),
    notes: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Update ticket status."""
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = new_status
    if notes:
        ticket.admin_notes = notes
    if new_status in ("resolved", "closed"):
        ticket.resolved_at = datetime.utcnow()

    await session.commit()
    return {"status": "updated", "ticket_id": ticket_id, "new_status": new_status}


@router.get("/feedback-summary")
async def feedback_summary(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
):
    """Summarize user feedback (thumbs up/down) for the period."""
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(UserFeedback).where(UserFeedback.created_at >= since)
    )
    feedbacks = result.scalars().all()

    total = len(feedbacks)
    positive = sum(1 for f in feedbacks if f.is_positive)
    negative = total - positive

    # By type
    by_type = {}
    for f in feedbacks:
        ft = f.feedback_type or "general"
        if ft not in by_type:
            by_type[ft] = {"positive": 0, "negative": 0}
        if f.is_positive:
            by_type[ft]["positive"] += 1
        else:
            by_type[ft]["negative"] += 1

    return {
        "days": days,
        "total": total,
        "positive": positive,
        "negative": negative,
        "satisfaction_pct": round(positive / total * 100, 1) if total > 0 else None,
        "by_type": by_type,
    }
