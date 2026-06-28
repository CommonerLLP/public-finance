# Flow graph — the inter-tier money-movement topology

The structured form of `notes/fund_flow_map.md` §1–§2: **who moves money to whom,
through which mechanism, under what authority and control rail.** It is the vertical
generalisation of the single-state Sankey (`viz/sankey/`) — that models one tier's
sources→uses; this models the transfers *between* tiers.

This is the **typology**, not instance data. Edges carry mechanism / authority /
conditionality / control-rail and a `concept_id` into the crosswalk
(`references/crosswalk/`) plus the verified chart head the flow lands under. Actual
₹ amounts for a given state/year are instance data layered on top later — none are
asserted here.

## Model

- `nodes.json` — fiscal entities + rails. `node_id`, `type`
  (`economy | union | state | ulb | pri | rail`), `label`, `chart` (which COA it
  keeps), `basis` (cash|accrual), `notes`. The `economy` node is the ultimate source
  (tax base / market); the `rail_*` nodes are PFMS/SNA, CNA, and RBI e-Kuber.
- `edges.json` — directed transfer mechanisms. `edge_id`, `from`, `to`,
  `mechanism`, `authority` (constitutional article), `conditionality`
  (`unconditional_formula | semi_tied | tied_uc_gated | discretionary | debt |
  own_source`), `control_rail` (`direct | treasury | sna | sna_sparsh | cna | none`),
  `route_via` (rail node ids the flow passes through, if any), `concept_id`
  (crosswalk), `lands_under` (chart:head at the receiving end, or null/TODO),
  `notes`.

Edges reference crosswalk concepts and (where known) verified chart heads, so the
three artifacts compose: **flow graph (who/how) → crosswalk (what concept) →
chart of accounts (which head, verified)**.

## What it answers

- **Inflows to a tier:** all edges `to: state` = every way a state is funded
  (own revenue + devolution + grants + CSS + loans).
- **The control story:** filter edges by `control_rail in {sna, sna_sparsh, cna}` =
  exactly the CSS/CS channel the Centre now throttles (fund_flow_map §2). Compare to
  the `direct` devolution edge — the unconditional vs throttled split is one query.
- **Trace a rupee vertically:** follow `route_via` — a CSS rupee goes
  `union → rail_rbi → rail_sna → state` under SNA-SPARSH, where the older direct
  grant went `union → state`.

## Status

- Encodes the verified mechanism topology (authorities/rails cited in
  `fund_flow_map.md`; article numbers flagged there for pinning).
- `lands_under` is filled where the crosswalk has a verified head (fc_grant→lmmha
  1601, octroi_comp→gmam 18133, loans→lmmha 7601); CSS/devolution heads are TODO.
- Next: instance overlay (attach a state-year's ₹ amounts per edge from the Sankey
  adapters) to render a vertical Sankey.
