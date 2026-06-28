# Crosswalk — one fiscal vocabulary across four charts of account

The four tiers will never share a code (cash vs accrual; four authorities — see
`notes/fund_flow_map.md` §0). This directory is the layer that makes them
*comparable anyway*: a small **pivot vocabulary of fiscal concepts**, plus
**mappings** from each chart's heads to those concepts.

It answers the repo's two standing questions:
- **Horizontal** — compare the same concept across states/cities (e.g. "contractor
  penalties", "interest paid") even though Gujarat calls it `23306`, NMAM calls it
  `140-20`, and a state budget calls it something else.
- **Vertical** — trace a concept across tiers (e.g. "money from above" = the state's
  tax devolution *and* the city's octroi-compensation grant `18133`), by walking the
  concept hierarchy.

## Design

**Pivot = GFSM 2014 + COFOG, not a bespoke scheme.** The IMF Government Finance
Statistics economic classification (taxes, grants, interest, sales, fines, …) and
the COFOG functional classification (health, water, general services, …) exist
precisely to make heterogeneous government accounts comparable, and are tier- and
country-neutral. We anchor every concept to a GFS and/or COFOG code rather than
invent meanings. *(Codes here are approximate until pinned to GFSM 2014 / COFOG —
flagged per concept.)*

**Two facets, because a budget line has two classifications.** Every line is both an
*economic nature* (what kind of money) and — for spending — a *function* (what it's
for). "Interest on PF" is economic:interest, function:n/a; "water supply staff
salary" is economic:compensation, function:water. Concepts carry `facet:
economic | functional` accordingly.

**SKOS mapping relations, reusing repo idiom.** Mappings are rarely 1:1 — one LMMHA
minor head can equal several NMAM detailed heads. So each mapping carries a SKOS
relation (`exactMatch | broadMatch | narrowMatch | relatedMatch`), the same
vocabulary the repo's LMMHA LOD already uses (`publicfinance/lmmha_skos_exporter.py`).
JSON is the working/tracked form; it can be exported to SKOS/TTL later via that
pattern. No new relation vocabulary invented.

**Hierarchy via dotted ids.** `concept_id` is dotted and hierarchical
(`rev.nontax.fines.contractor_penalty`). Broader/narrower is implied by truncation —
`rev.nontax.fines` is the parent of `…contractor_penalty`. The vertical view = query
all narrower concepts of `rev.transfer.from_above` and collect their mapped heads
across every chart.

## Files

- `concepts.json` — the pivot registry. One row per concept:
  `concept_id`, `label`, `facet`, `kind` (revenue|expense|financing),
  `gfs`, `cofog` (approx, nullable), `tier_role`
  (own_source|transfer_from_above|transfer_to_below|application|financing), `notes`.
- `mappings.json` — head→concept edges. One row per mapped head:
  `chart` (lmmha|nmam|gmam|masp), `head_code`, `head_name`, `concept_id`,
  `relation` (SKOS), `source_ref` (a `verified_facts.md` id where possible).

A head is only mapped here once its definition is verified (logged in
`memory/verified_facts.md`). Unverified heads are left out, not guessed.

## Worked examples

- **Horizontal:** concept `rev.nontax.fines.contractor_penalty` ← GMAM `23306`
  (exactMatch) and ← NMAM `140-20` Penalties & Fines (broadMatch — NMAM doesn't
  split contractor vs supplier). Aggregating the concept gives a like-for-like
  cross-city series despite different codes.
- **Vertical:** `rev.transfer.from_above` has narrower concepts
  `…tax_devolution` (state, LMMHA), `…fc_grant`, `…css`, and `…octroi_comp` (city,
  GMAM `18133`). One query over the subtree = every "from above" line at every tier —
  the canonical `18133` three-tier test case.

## Status / next

- Seed covers the **verified** heads in hand: GMAM `23xxx` + `18133`, and the NMAM
  income major heads. LMMHA and MASP mappings are the next pass (needs their code
  lists confirmed, not guessed).
- This is the target vocabulary for the typed fiscal-flow graph in
  `notes/fund_flow_map.md` §4: each transfer edge's endpoints carry `concept_id`s.
- Pin GFS/COFOG codes to GFSM 2014 / COFOG before any public citation.
