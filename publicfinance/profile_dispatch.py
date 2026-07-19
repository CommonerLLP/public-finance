"""CLI helpers for budget document profile dispatch."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from publicfinance import budget_document_profiles as profiles


def _split_csv(values: str | None) -> tuple[str, ...] | None:
    if not values:
        return None
    entries = tuple(part.strip() for part in values.split(","))
    return tuple(entry for entry in entries if entry)


def _print_profiles(
    state: str,
    fy: str,
    *,
    intent: str | None,
    document_families: tuple[str, ...] | None,
    document_types: tuple[str, ...] | None,
) -> None:
    selected = profiles.document_profiles_for_dispatch(
        state,
        fy,
        intent=intent,
        document_families=document_families,
    )
    if document_types is not None:
        selected = tuple(
            profile
            for profile in selected
            if profile.document_type in document_types
        )

    payload = {
        "state": state,
        "fy": fy,
        "intent": intent,
        "document_count": len(selected),
        "document_types": [profile.document_type for profile in selected],
        "document_families": sorted({profile.document_family for profile in selected}),
        "profiles": [asdict(profile) for profile in selected],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_summary(state: str, fy: str) -> None:
    print(json.dumps(profiles.state_profile_summary(state, fy), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch budget document profiles for a state and FY.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--fy", required=True)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument(
        "--intent",
        choices=("be_re", "codes", "scheme_info"),
    )
    parser.add_argument(
        "--document-families",
        help="Comma-separated document families to filter (for example: budget_book,thematic_budget).",
    )
    parser.add_argument(
        "--document-types",
        help="Comma-separated document types to filter (for example: summary_budget,budget_statement_capital_expenditure).",
    )
    args = parser.parse_args()

    families = _split_csv(args.document_families)
    types = _split_csv(args.document_types)

    if args.summary:
        _print_summary(args.state, args.fy)
        return

    _print_profiles(
        args.state,
        args.fy,
        intent=args.intent,
        document_families=families,
        document_types=types,
    )


if __name__ == "__main__":
    main()
