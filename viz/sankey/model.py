"""Port (domain contract) for the money-flow Sankey.

Adapters read a state-specific source (CivicDataLab Excel, Gujarat demand
books, RBI State-Finances appendices) and return one of these normalised
models. The core builder consumes only these — never a raw source — so a new
state is a new adapter, not a new builder.

All amounts are INR crore.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExpenditureLine:
    """One budget line, normalised to (major head, amount in crore)."""

    major_head: str
    amount_cr: float


@dataclass
class SectorModel:
    """Uses-side input: expenditure lines to roll up into functional sectors."""

    state: str
    fy: str
    lines: list[ExpenditureLine]
    source: str
    caveat: str
    basis: str = ""  # e.g. "Budget Estimate", "Actuals"


@dataclass(frozen=True)
class Flow:
    """One source or use in the balanced Sankey."""

    label: str
    amount_cr: float
    kind: str   # sources: own|transfer|borrow|misc ; uses: use
    color: str


@dataclass
class BalanceModel:
    """Two-sided input: sources fund the exchequer, exchequer funds uses.

    Net borrowing (the gross fiscal deficit) is the financing residual the
    adapter computes; sources and uses must balance by the fiscal identity.
    """

    state: str
    fy: str
    sources: list[Flow]
    uses: list[Flow]
    source: str
    caveat: str
    legend: list[dict] = field(default_factory=list)
    headline: str = ""
