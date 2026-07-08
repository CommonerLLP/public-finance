# Off-budget / contingent-liability slices — one file per jurisdiction

The data behind the **"Beyond the budget — guarantees"** view in `flow.html`. This
is the part of public finance that sits *outside* the budget total: government
guarantees of PSU/SPV/ULB debt (contingent liabilities) and off-budget borrowing
routed through state/Union entities to bypass borrowing ceilings.

**It is never summed into the on-budget total.** Guarantees become a charge on the
Consolidated Fund only if invoked; off-budget borrowings are off the books by
design. The view is a separate toggle for exactly that reason.

## Modular by design — scales to all states / UTs / the Union

One normalised file per jurisdiction: `references/offbudget/<code>.json`. The
pipeline is file-driven end to end:

```
references/offbudget/<code>.json          ← the only thing you add per jurisdiction
  → viz/sankey/adapters/offbudget.py      (generic load(code, fy) → OffBudgetModel)
  → viz/sankey/core.build_offbudget        (model → {meta,nodes,links})
  → viz/build_sankey.py --view offbudget   (no per-jurisdiction code)
  → viz/build_sankey_manifest.py           (scans built files → manifest)
  → references/lmmha/lod/flow.html         (one renderer, picker auto-populates)
```

**Adding a jurisdiction-year is: drop/extend a JSON file, then run**

```bash
python -m viz.build_sankey --state <code> --fy <fy> --view offbudget
python -m viz.build_sankey_manifest
```

No code edit. The state/UT/Union picker and year dropdown fill themselves from the
manifest. Jurisdiction label + type (state | ut | union) come from the registry in
`build_sankey_manifest.py` (default: title-case + "state").

## Schema (`offbudget-jurisdiction-v1`)

```jsonc
{
  "jurisdiction": {"code": "gujarat", "type": "state", "label": "Gujarat"},
  "guarantee_ceiling_cr": 20000,            // statutory cap, or null
  "guarantee_statute": "Gujarat State Guarantees Act, 1963",
  "outstanding_series_cr": {"2018-19": 4699, ...},   // multi-year context
  "years": {
    "2024-25": {
      "outstanding_cr": 1421,
      "pct_of_revenue_receipts": 0.65,
      "beneficiaries": [                    // named exposures; builder adds "Other"
        {"label": "...", "amount_cr": 345, "kind": "psu_power"}
      ],
      "off_budget_note": "...",
      "source": "CAG SFAR ... (Report No. ...)"
    }
  },
  "caveat": "...",
  "provenance": { "sources": {"<fy>": {"url","sha256","pages","text"}}, "raw_pdfs": "..." }
}
```

`kind` ∈ `psu_power | psu_other | ulb | spv | board | coop | other` → drives the
beneficiary colour in `core.OFFBUDGET_COLOR`.

## Source of truth

State/UT: the **CAG State Finances Audit Report** (SFAR), drawn from Statement 20
of the Finance Accounts — the audit gold standard for contingent liabilities.
Union: the CAG Union Government Finance Accounts / Union Finances reports (e.g.
NSSF, guarantees, oil/fertiliser arrangements). Cross-check against **RBI "State
Finances: A Study of Budgets"** guarantee statements where possible (two-source
rule). Raw PDFs live per-source under `references/cag_<juris>/source/` (gitignored).

## Coverage

| Jurisdiction | Measure (leads with) | Years | Source |
|---|---|---|---|
| Gujarat | outstanding guarantees (₹4,699 cr 2018-19 → ₹1,421 cr 2024-25) | 2018-19, 2020-21 … 2024-25 (2019-20 not published) | CAG SFAR (Reports 1/2024, 1/2025, 2/2026) |
| Kerala | off-budget SPV borrowing (₹32,942 cr via KIIFB + KSSPL) | 2023-24 | CAG SFAR 2023-24 |

The two leading measures differ on purpose — the view shows each jurisdiction's
*dominant* off-books mechanism (`measure` field). Gujarat's story is guarantees;
Kerala's is undisclosed SPV borrowing, now sub judice. That contrast is the point.

Grows one acquisition at a time. Partial coverage is honest — the picker only
offers years that exist.
