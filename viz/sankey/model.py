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


@dataclass(frozen=True)
class Beneficiary:
    """One entity whose debt the government guarantees (a contingent liability)."""

    label: str
    amount_cr: float
    kind: str   # psu_power | psu_other | ulb | spv | board | coop | other
    color: str


@dataclass
class OffBudgetModel:
    """Off-budget / contingent-liability input for any jurisdiction-year.

    This is NOT part of the on-budget total — guarantees become a charge on the
    Consolidated Fund only if invoked; off-budget borrowings sit outside the
    budget by design. Jurisdiction-agnostic: a state, UT or the Union populates
    the same shape. Amounts in INR crore.
    """

    jurisdiction: str          # display label, e.g. "Gujarat", "Union of India"
    jtype: str                 # state | ut | union
    fy: str
    ceiling_cr: float | None   # statutory guarantee ceiling, if any
    outstanding_cr: float      # the headline off-books stock (see `measure`)
    beneficiaries: list[Beneficiary]   # named exposures; builder adds "Other"
    series_cr: dict            # {fy: outstanding_cr} multi-year, for context
    source: str
    caveat: str
    # which off-books stock this jurisdiction leads with — guarantees (Gujarat) or
    # off-budget SPV borrowing (Kerala/KIIFB). Drives the root node + headline.
    measure: str = "outstanding guarantees"
    pct_label: str = "revenue receipts"   # what pct_of is a share of
    pct_of: float | None = None
    off_budget_note: str = ""
    statute: str = ""
