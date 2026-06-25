"""Bridge budget-crawler's Union-Budget + RBI acquisition to commoner-probe.

Acquisition of the Union Budget SBE spreadsheets and the RBI "State Finances"
documents now lives in the published ``commoner-probe`` package (``BudgetProbe``).
This module runs the probe and indexes each downloaded file into the existing
SQLite ``budget_docs`` table via :func:`metadata.index_budget_doc`, so the
downstream analysis (``extract_scheme_data``, ``parse_demand_xls``) — which reads
file paths from the DB, not from the scraper — keeps working unchanged.

The probe writes under ``<out_dir>/<source-name>/<filename>``; the analysis is
path-driven (it reads ``local_path`` from ``budget_docs``), so the exact layout
does not matter as long as we index the probe's real ``dest``.

Only Union + RBI are delegated. The state / Gujarat / CMO scrapers have no probe
equivalent yet and are untouched.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import DEFAULT_DB_PATH, index_budget_doc, make_doc_id  # noqa: E402

from commoner_probe.budget.probe import BudgetProbe  # noqa: E402

# Probe statuses that mean "a file exists on disk and should be indexed".
_INDEXABLE = {"downloaded", "skipped_exists"}


def run_union_budget(
    demand_no: str,
    out_dir,
    db_path=DEFAULT_DB_PATH,
    dry_run: bool = False,
    sleep: float = 2.0,
) -> tuple[list[dict], int]:
    """Acquire Union Budget SBE files for one demand via BudgetProbe; index each.

    Returns ``(records, indexed_count)``.
    """
    probe = BudgetProbe(Path(out_dir), demands=[str(demand_no)], sleep=sleep)
    records = probe.probe_sources(["union-budget"], dry_run=dry_run)

    indexed = 0
    for rec in records:
        if rec.get("status") not in _INDEXABLE:
            continue
        ext = rec["filename"].rsplit(".", 1)[-1]
        doc_id = make_doc_id("central", rec["demand_no"], rec["fiscal_year"])
        index_budget_doc(
            doc_id=doc_id,
            state="central",
            fiscal_year=rec["fiscal_year"],
            document_type="demand_for_grants",
            source_url=rec["url"],
            local_path=rec["dest"],
            file_extension=ext,
            ministry="MWCD",
            db_path=db_path,
        )
        indexed += 1
    return records, indexed


def run_rbi(
    out_dir,
    db_path=DEFAULT_DB_PATH,
    dry_run: bool = False,
    rbi_url: str | None = None,
    sleep: float = 1.0,
) -> tuple[list[dict], int]:
    """Discover + acquire RBI State-Finances documents via BudgetProbe; index each.

    Returns ``(records, indexed_count)``.
    """
    probe = BudgetProbe(Path(out_dir), sleep=sleep, **({"rbi_url": rbi_url} if rbi_url else {}))
    records = probe.probe_sources(["rbi-state-finances"], dry_run=dry_run)

    indexed = 0
    for rec in records:
        if rec.get("status") not in _INDEXABLE:
            continue
        stem, _, ext = rec["filename"].rpartition(".")
        doc_id = make_doc_id("rbi", rec["fiscal_year"], rec.get("section"), stem, ext)
        index_budget_doc(
            doc_id=doc_id,
            state="All_States_RBI",
            fiscal_year=rec["fiscal_year"],
            document_type=stem,
            source_url=rec["url"],
            local_path=rec["dest"],
            file_extension=ext,
            db_path=db_path,
        )
        indexed += 1
    return records, indexed
