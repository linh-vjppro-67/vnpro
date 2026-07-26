from decimal import Decimal
from fastapi import HTTPException

LEAD_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"CONTACTED", "DISQUALIFIED"},
    "CONTACTED": {"QUALIFIED", "DISQUALIFIED"},
    "QUALIFIED": {"CONVERTED", "DISQUALIFIED"},
    "CONVERTED": set(),
    "DISQUALIFIED": set(),
}

OPPORTUNITY_TRANSITIONS: dict[str, set[str]] = {
    "LEAD": {"QUALIFICATION", "LOST"},
    "QUALIFICATION": {"TECHNICAL_SURVEY", "LOST"},
    "TECHNICAL_SURVEY": {"PROPOSAL", "LOST"},
    "PROPOSAL": {"NEGOTIATION", "LOST"},
    "NEGOTIATION": {"WON", "LOST"},
    "WON": set(),
    "LOST": set(),
}

# REVIEWING is reserved for a future phase (a distinct human-triage step before a decision is
# made); phase 1 never sets it — "awaiting decision" is expressed by ApprovalRequest.status,
# not by a second Quotation status.
QUOTATION_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "REVIEWING": {"APPROVED", "REJECTED"},
    "APPROVED": {"SENT_TO_CUSTOMER"},
    "REJECTED": {"DRAFT"},
    "SENT_TO_CUSTOMER": {"WON", "LOST", "EXPIRED"},
    "WON": set(),
    "LOST": set(),
    "EXPIRED": set(),
}

CONTRACT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"INTERNAL_REVIEW", "CANCELLED"},
    "INTERNAL_REVIEW": {"APPROVED", "DRAFT", "CANCELLED"},
    "APPROVED": {"SENT_FOR_SIGNATURE", "CANCELLED"},
    "SENT_FOR_SIGNATURE": {"SIGNED", "CANCELLED"},
    "SIGNED": {"ACTIVE"},
    "ACTIVE": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

WORK_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "PLANNED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"DONE", "CANCELLED"},
    "DONE": set(),
    "CANCELLED": set(),
}

ACCEPTANCE_RECORD_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "REJECTED": {"DRAFT"},
    "APPROVED": set(),
}

PURCHASE_REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "REJECTED": {"DRAFT"},
    "APPROVED": {"CONVERTED"},
    "CONVERTED": set(),
}

PURCHASE_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"ORDERED", "CANCELLED"},
    "ORDERED": {"PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CANCELLED"},
    "PARTIALLY_RECEIVED": {"FULLY_RECEIVED", "CANCELLED"},
    "FULLY_RECEIVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
}

STOCK_RESERVATION_TRANSITIONS: dict[str, set[str]] = {
    "RESERVED": {"FULFILLED", "RELEASED"},
    "FULFILLED": set(),
    "RELEASED": set(),
}

TASK_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"DONE_PENDING_REVIEW", "CANCELLED"},
    "DONE_PENDING_REVIEW": {"CONFIRMED", "IN_PROGRESS"},
    "CONFIRMED": set(),
    "CANCELLED": set(),
}

TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "LEAD": LEAD_TRANSITIONS,
    "OPPORTUNITY": OPPORTUNITY_TRANSITIONS,
    "QUOTATION": QUOTATION_TRANSITIONS,
    "CONTRACT": CONTRACT_TRANSITIONS,
    "WORK_ORDER": WORK_ORDER_TRANSITIONS,
    "ACCEPTANCE_RECORD": ACCEPTANCE_RECORD_TRANSITIONS,
    "PURCHASE_REQUEST": PURCHASE_REQUEST_TRANSITIONS,
    "PURCHASE_ORDER": PURCHASE_ORDER_TRANSITIONS,
    "STOCK_RESERVATION": STOCK_RESERVATION_TRANSITIONS,
    "TASK": TASK_TRANSITIONS,
}

# what approve/reject land on, per entity type — used by the generic /approvals/{id}/decide route
DECISION_TARGETS: dict[str, dict[str, str]] = {
    "QUOTATION": {"approved": "APPROVED", "rejected": "REJECTED"},
    "CONTRACT": {"approved": "APPROVED", "rejected": "DRAFT"},
    "ACCEPTANCE_RECORD": {"approved": "APPROVED", "rejected": "REJECTED"},
    "PURCHASE_REQUEST": {"approved": "APPROVED", "rejected": "REJECTED"},
}

DISCOUNT_APPROVAL_THRESHOLD_PERCENT = Decimal("15")
LARGE_DEAL_VALUE_THRESHOLD = Decimal("500000000")
LARGE_PROJECT_BUDGET_THRESHOLD = Decimal("800000000")


def assert_transition(entity_type: str, current: str, target: str) -> None:
    allowed = TRANSITIONS.get(entity_type, {}).get(current, set())
    if target not in allowed:
        raise HTTPException(409, f"Không thể chuyển {entity_type} từ {current} sang {target}")


def quotation_needs_director_approval(total_amount: Decimal, max_discount_percent: Decimal) -> bool:
    return max_discount_percent > DISCOUNT_APPROVAL_THRESHOLD_PERCENT or total_amount > LARGE_DEAL_VALUE_THRESHOLD


def acceptance_needs_director_approval(project_budget: Decimal) -> bool:
    return project_budget > LARGE_PROJECT_BUDGET_THRESHOLD
