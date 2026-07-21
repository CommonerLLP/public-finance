"""Registry of state budget document profiles and parser/OCR defaults."""

from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import subprocess
import re
from typing import Sequence

REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PdfWindow:
    code_family: str
    target_codes: tuple[str, ...]
    source_relpath: str
    page_start: int
    page_end: int
    unit: str
    parser_hint: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OCRConfig:
    source_type: str
    extraction_mode: str
    languages: tuple[str, ...]
    legacy_font_maps: tuple[str, ...] = ()
    dpi: int | None = None
    expect_tables: bool = True
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParserConfig:
    strategy: str
    unit: str
    code_axis: str
    amount_columns: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BudgetDocumentProfile:
    state: str
    fy: str
    document_type: str
    source_relpath: str
    document_family: str
    ocr: OCRConfig
    parser: ParserConfig
    can_extract_be_re: bool
    can_extract_codes: bool
    can_extract_scheme_info: bool
    windows: tuple[PdfWindow, ...] = ()
    notes: tuple[str, ...] = ()


RAJASTHAN_REVENUE_SOCIAL_2025_26 = BudgetDocumentProfile(
    state="Rajasthan",
    fy="2025-26",
    document_type="budget_statement_revenue_social_services",
    source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 2c _ Revenue Expenditure-Social Services.pdf",
    document_family="budget_book",
    ocr=OCRConfig(
        source_type="pdf_text",
        extraction_mode="pdftotext-layout",
        languages=("Hindi", "English"),
        legacy_font_maps=("devlys-010", "krutidev"),
        dpi=300,
        notes=(
            "Text-bearing PDF; do not force OCR first.",
            "Hindi labels are noisy; the font hints matter mainly for fallback normalization.",
        ),
    ),
    parser=ParserConfig(
        strategy="lmmha_code_window",
        unit="lakh",
        code_axis="major-submajor-minor",
        amount_columns="budget_estimate_2025_26",
        notes=(
            "Anchor on code blocks and sub-major totals before considering label semantics.",
            "Prefer fixed page windows over whole-document sweeps.",
        ),
    ),
    can_extract_be_re=True,
    can_extract_codes=True,
    can_extract_scheme_info=True,
    windows=(
        PdfWindow(
            code_family="2205",
            target_codes=("2202-00-105", "2205-00-105"),
            source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 2c _ Revenue Expenditure-Social Services.pdf",
            page_start=80,
            page_end=125,
            unit="lakh",
            parser_hint="Detailed revenue-expenditure spread covering public-library entries around the 2205/2202 family family drift.",
            notes=(
                "2205 is the canonical major in the current text extracts; keep 2202 accepted as an alias for noisy/variant OCR.",
                "Current extraction places the target family near the end of the section.",
            ),
        ),
    ),
)

RAJASTHAN_CAPITAL_2025_26 = BudgetDocumentProfile(
    state="Rajasthan",
    fy="2025-26",
    document_type="budget_statement_capital_expenditure",
    source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 3a _ Capital Expenditure.pdf",
    document_family="budget_book",
    ocr=OCRConfig(
        source_type="pdf_text",
        extraction_mode="pdftotext-layout",
        languages=("Hindi", "English"),
        legacy_font_maps=("devlys-010", "krutidev"),
        dpi=300,
    ),
    parser=ParserConfig(
        strategy="lmmha_code_window",
        unit="lakh",
        code_axis="major-submajor-minor",
        amount_columns="budget_estimate_2025_26",
        notes=(
            "4202 capital pages should be read functionally alongside their 2202 revenue twin.",
            "Sub-major totals are the stable first-pass anchor in this book.",
        ),
    ),
    can_extract_be_re=True,
    can_extract_codes=True,
    can_extract_scheme_info=True,
    windows=(
        PdfWindow(
            code_family="4202",
            target_codes=("4202-04-105",),
            source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 3a _ Capital Expenditure.pdf",
            page_start=27,
            page_end=32,
            unit="lakh",
            parser_hint="Early 4202 section with the stable sub-major 04 total anchor used for education capital outlay.",
            notes=(
                "The 4202 section starts at PDF page 27.",
                "Current extraction shows the sub-major 04 total in this window.",
            ),
        ),
    ),
)

RAJASTHAN_LOANS_2025_26 = BudgetDocumentProfile(
    state="Rajasthan",
    fy="2025-26",
    document_type="budget_statement_public_debt_loans_public_account",
    source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 3b _ Public Debt, Loan, Public Account Volume.pdf",
    document_family="budget_book",
    ocr=OCRConfig(
        source_type="pdf_text",
        extraction_mode="pdftotext-layout",
        languages=("Hindi", "English"),
        legacy_font_maps=("devlys-010", "krutidev"),
        dpi=300,
    ),
    parser=ParserConfig(
        strategy="loan_ledger_window",
        unit="lakh",
        code_axis="major-head-first",
        amount_columns="balance_and_budget_2025_26",
        notes=(
            "This book is a loans ledger, not a standard revenue/capital service table.",
            "Verify any down-mapping from 6202 major-head totals to minor heads before reuse.",
        ),
    ),
    can_extract_be_re=True,
    can_extract_codes=True,
    can_extract_scheme_info=False,
    windows=(
        PdfWindow(
            code_family="6202",
            target_codes=("6202",),
            source_relpath="data/state_budgets/Rajasthan/2025-26/State Budget/Volume 3b _ Public Debt, Loan, Public Account Volume.pdf",
            page_start=81,
            page_end=84,
            unit="lakh",
            parser_hint="Loans-division summary and detailed 6202 pages; stable for major-head extraction.",
            notes=(
                "The loans division summary points to detailed 6202 pages at 81-84.",
                "Minor-head mapping is not yet verified.",
            ),
        ),
    ),
)

RAJASTHAN_BASE_PROFILE = {
    "state": "Rajasthan",
    "fy": "2025-26",
    "ocr": OCRConfig(
        source_type="pdf_text",
        extraction_mode="pdftotext-layout",
        languages=("Hindi", "English"),
        legacy_font_maps=("devlys-010", "krutidev"),
        dpi=300,
    ),
}


def _rajasthan_doc(
    document_type: str,
    filename: str,
    document_family: str,
    *,
    can_extract_be_re: bool,
    can_extract_codes: bool,
    can_extract_scheme_info: bool,
    parser_strategy: str,
    parser_unit: str = "lakh",
    code_axis: str = "none",
    amount_columns: str = "varies",
    notes: tuple[str, ...] = (),
) -> BudgetDocumentProfile:
    return BudgetDocumentProfile(
        state=RAJASTHAN_BASE_PROFILE["state"],
        fy=RAJASTHAN_BASE_PROFILE["fy"],
        document_type=document_type,
        source_relpath=f"data/state_budgets/Rajasthan/2025-26/State Budget/{filename}",
        document_family=document_family,
        ocr=replace(RAJASTHAN_BASE_PROFILE["ocr"]),
        parser=ParserConfig(
            strategy=parser_strategy,
            unit=parser_unit,
            code_axis=code_axis,
            amount_columns=amount_columns,
            notes=notes,
        ),
        can_extract_be_re=can_extract_be_re,
        can_extract_codes=can_extract_codes,
        can_extract_scheme_info=can_extract_scheme_info,
        notes=notes,
    )


RAJASTHAN_2025_26_DOCUMENTS = (
    _rajasthan_doc(
        "summary_budget",
        "Volume 1 _ Summary Volume.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=False,
        parser_strategy="summary_table",
        code_axis="major-head",
        amount_columns="actuals_re_budget_be",
        notes=("High-level fiscal and head-wise summaries.",),
    ),
    _rajasthan_doc(
        "revenue_receipts_statement",
        "Volume 2a _ Revenue Receipts Volume.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=False,
        parser_strategy="receipt_code_window",
        code_axis="major-submajor-minor",
        amount_columns="actuals_re_budget_be",
        notes=("Revenue receipts and tax/non-tax code hierarchy.",),
    ),
    _rajasthan_doc(
        "revenue_expenditure_general",
        "Volume 2b _ Revenue Expenditure-General Services.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="lmmha_code_window",
        code_axis="major-submajor-minor-object",
        amount_columns="actuals_re_budget_be",
        notes=("Detailed general-services expenditure tables.",),
    ),
    RAJASTHAN_REVENUE_SOCIAL_2025_26,
    _rajasthan_doc(
        "revenue_expenditure_economic",
        "Volume 2d _ Revenue Expenditure-Economic Services.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="lmmha_code_window",
        code_axis="major-submajor-minor-object",
        amount_columns="actuals_re_budget_be",
        notes=("Detailed economic-services expenditure tables.",),
    ),
    RAJASTHAN_CAPITAL_2025_26,
    RAJASTHAN_LOANS_2025_26,
    _rajasthan_doc(
        "post_volume",
        "Volume 4a _ Post Volume.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="departmental_detail",
        code_axis="demand-post",
        amount_columns="budget_be",
        notes=("Administrative post and staffing detail, not primary fiscal classification.",),
    ),
    _rajasthan_doc(
        "grant_loan_investment",
        "Volume 4b _ Grant_Loan_Investment.pdf",
        "budget_book",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="grant_loan_detail",
        code_axis="demand-scheme",
        amount_columns="budget_be",
        notes=("Grant, loan, and investment detail with scheme-like labels.",),
    ),
    _rajasthan_doc(
        "pwd_works_part_i_1",
        "Volume 4c _ Details of PWD Works Part I-1.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
        notes=("PWD work-level project register.",),
    ),
    _rajasthan_doc(
        "pwd_works_part_i_2",
        "Volume 4c _ Details of PWD Works Part I-2.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_1",
        "Volume 4c _ Details of PWD Works Part II-1.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_2",
        "Volume 4c _ Details of PWD Works Part II-2.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_3",
        "Volume 4c _ Details of PWD Works Part II-3.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_4",
        "Volume 4c _ Details of PWD Works Part II-4.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_5",
        "Volume 4c _ Details of PWD Works Part II-5.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_6",
        "Volume 4c _ Details of PWD Works Part II-6.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_7",
        "Volume 4c _ Details of PWD Works Part II-7.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "pwd_works_part_ii_8",
        "Volume 4c _ Details of PWD Works Part II-8.pdf",
        "works_book",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="works_register",
        parser_unit="lakh",
        code_axis="work-item",
        amount_columns="work_estimates",
    ),
    _rajasthan_doc(
        "agriculture_budget",
        "Volume 4d _ Agriculture Budget.pdf",
        "thematic_budget",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="thematic_budget_book",
        code_axis="department-scheme-head",
        amount_columns="budget_be",
        notes=("Useful for scheme framing in the agriculture domain.",),
    ),
    _rajasthan_doc(
        "green_budget",
        "Volume 4e _ Green Budget.pdf",
        "thematic_budget",
        can_extract_be_re=True,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="theme_tagged_budget",
        code_axis="theme-programme",
        amount_columns="budget_be",
    ),
    _rajasthan_doc(
        "budget_at_a_glance",
        "Budget at a Glance 2025-2026.pdf",
        "analytical_note",
        can_extract_be_re=True,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="summary_note",
        parser_unit="crore",
        code_axis="none",
        amount_columns="headline_tables",
    ),
    _rajasthan_doc(
        "budget_study",
        "Budget Study 2025-2026.pdf",
        "analytical_note",
        can_extract_be_re=True,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="analytical_report",
        parser_unit="crore",
        code_axis="theme",
        amount_columns="headline_tables",
    ),
    _rajasthan_doc(
        "budget_related_analytical_statement",
        "Budget related Analytical Statement.pdf",
        "analytical_note",
        can_extract_be_re=True,
        can_extract_codes=True,
        can_extract_scheme_info=True,
        parser_strategy="analytical_statement",
        code_axis="head-theme",
        amount_columns="derived_tables",
    ),
    _rajasthan_doc(
        "economic_review_english",
        "Economic Review 2024-2025 - English.pdf",
        "economic_review",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="economic_review",
        parser_unit="mixed",
        code_axis="theme",
        amount_columns="derived_tables",
    ),
    _rajasthan_doc(
        "economic_review_hindi",
        "Economic Review 2024-2025 - Hindi.pdf",
        "economic_review",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="economic_review",
        parser_unit="mixed",
        code_axis="theme",
        amount_columns="derived_tables",
    ),
    _rajasthan_doc(
        "frbm_document",
        "FRBM Document.pdf",
        "fiscal_framework",
        can_extract_be_re=True,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="frbm_tables",
        parser_unit="crore",
        code_axis="indicator",
        amount_columns="macro_fiscal_projections",
    ),
    _rajasthan_doc(
        "output_outcome_budget",
        "Output-Outcome Budget 2025-26.pdf",
        "scheme_outcomes",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="scheme_outcome_book",
        parser_unit="mixed",
        code_axis="department-scheme-output",
        amount_columns="outputs_outcomes",
        notes=("Best source for scheme/programme narrative and output indicators.",),
    ),
    _rajasthan_doc(
        "budget_speech",
        "Budget Speech 2025-2026 (19.02.2025).pdf",
        "speech",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="speech_text",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
    _rajasthan_doc(
        "press_note_english",
        "Press Note - English.pdf",
        "press_note",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="press_note",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
    _rajasthan_doc(
        "press_note_hindi",
        "Press Note - Hindi.pdf",
        "press_note",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="press_note",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
    _rajasthan_doc(
        "finance_bill",
        "Finance Bill.pdf",
        "legal",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="legal_text",
        parser_unit="none",
        code_axis="none",
        amount_columns="none",
    ),
    _rajasthan_doc(
        "finance_act",
        "Finance Act, 2025.pdf",
        "legal",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="legal_text",
        parser_unit="none",
        code_axis="none",
        amount_columns="none",
    ),
    _rajasthan_doc(
        "budget_notification",
        "Budget Notification.pdf",
        "legal",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="notification_text",
        parser_unit="none",
        code_axis="none",
        amount_columns="none",
    ),
    _rajasthan_doc(
        "vat_act",
        "Rajasthan Value Added Tax Act, 2025.pdf",
        "legal",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=False,
        parser_strategy="legal_text",
        parser_unit="none",
        code_axis="none",
        amount_columns="none",
    ),
    _rajasthan_doc(
        "reply_general_debate",
        "Announcements made by Hon'ble Deputy Chief Minister (Finance) on reply to General Debate on Budget 2025-2026 (27.02.2025).pdf",
        "speech",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="speech_text",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
    _rajasthan_doc(
        "appropriation_reply",
        "Announcements made by Hon’ble Chief Minister on Appropriation Bill Reply (12.03.2025).pdf",
        "speech",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="speech_text",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
)


RAJASTHAN_FY_FILENAME_OVERRIDES: dict[str, dict[str, str]] = {
    "2024-25": {
        "Budget at a Glance 2025-2026.pdf": "Budget at a Glance 2024-2025.pdf",
        "Budget Study 2025-2026.pdf": "Budget Study 2024-2025.pdf",
        "Economic Review 2024-2025 - English.pdf": "Economic Review 2023-2024 - English.pdf",
        "Economic Review 2024-2025 - Hindi.pdf": "Economic Review 2023-2024 - Hindi.pdf",
        "Finance Act, 2025.pdf": "Finance Act, 2024.pdf",
        "Announcements made by Hon’ble Chief Minister on Appropriation Bill Reply (12.03.2025).pdf": "Announcements made by Hon’ble Chief Minister on Appropriation Bill Reply (29.07.2024).pdf",
        "Announcements made by Hon'ble Deputy Chief Minister (Finance) on reply to General Debate on Budget 2025-2026 (27.02.2025).pdf": "Announcements made by Hon'ble Deputy Chief Minister (Finance) on reply to General Debate on Modified Budget 2024-2025 (16.07.2024).pdf",
        "Budget Speech 2025-2026 (19.02.2025).pdf": "Budget Speech 2024-2025 (10.07.2024).pdf",
    },
    "2023-24": {
        "Budget at a Glance 2025-2026.pdf": "Budget at a Glance 2023-2024.pdf",
        "Budget Study 2025-2026.pdf": "Budget Study 2023-2024.pdf",
        "Economic Review 2024-2025 - English.pdf": "Economic Review 2023-2024 - English.pdf",
        "Economic Review 2024-2025 - Hindi.pdf": "Economic Review 2023-2024 - Hindi.pdf",
        "Finance Act, 2025.pdf": "Finance Act, 2023.pdf",
        "Announcements made by Hon’ble Chief Minister on Appropriation Bill Reply (12.03.2025).pdf": "Announcement made by Honourable Chief Minister on Appropriation Bill Reply (17.03.2023).pdf",
        "Announcements made by Hon'ble Deputy Chief Minister (Finance) on reply to General Debate on Budget 2025-2026 (27.02.2025).pdf": "Announcements made by Honourable Chief Minister on reply to General Debate on Budget 2023-2024 (16.02.2023).pdf",
        "Budget Speech 2025-2026 (19.02.2025).pdf": "Budget 2023-2024 Speech of Honourable Chief Minister (English Version).pdf",
        "Rajasthan Value Added Tax Act, 2025.pdf": "Rajasthan Value Added Tax Act, 2025.pdf",
    },
    "2022-23": {
        "Budget at a Glance 2025-2026.pdf": "Budget at a Glance 2022-2023.pdf",
        "Budget Study 2025-2026.pdf": "Budget Study 2022-2023.pdf",
        "Economic Review 2024-2025 - English.pdf": "Economic Review 2022-2023 - English.pdf",
        "Economic Review 2024-2025 - Hindi.pdf": "Economic Review 2022-2023 - Hindi.pdf",
        "Finance Act, 2025.pdf": "Finance Act, 2022.pdf",
        "Announcements made by Hon’ble Chief Minister on Appropriation Bill Reply (12.03.2025).pdf": "Announcement made by Honourable Chief Minister on Appropriation Bill Reply (21.03.2022).pdf",
        "Announcements made by Hon'ble Deputy Chief Minister (Finance) on reply to General Debate on Budget 2025-2026 (27.02.2025).pdf": "Announcements made by Honourable Chief Minister on reply to General Debate on Budget 2022-2023 (03.03.2022).pdf",
        "Budget Speech 2025-2026 (19.02.2025).pdf": "Budget 2022-2023 Speeches of Chief Minister (English Version).pdf",
        "Rajasthan Value Added Tax Act, 2025.pdf": "Rajasthan Value Added Tax Act, 2025.pdf",
    },
}


def _fy_to_long_fy(fy: str) -> tuple[str, str]:
    start, end = fy.split("-")
    return fy, f"{start}-{start[:2]}{end}"


def _resolve_rajasthan_year_source(
    source_relpath: str,
    target_fy: str,
    *,
    filename_overrides: dict[str, str] | None = None,
) -> str | None:
    source_path = Path(source_relpath)
    filename = filename_overrides.get(source_path.name, source_path.name) if filename_overrides else source_path.name
    if filename == source_path.name:
        filename = filename.replace("2025-26", target_fy).replace("2025-2026", _fy_to_long_fy(target_fy)[1])
        filename = filename.replace("2025", target_fy.split("-")[0])

    candidate_dir = str(source_path.parent).replace("2025-26", target_fy)
    candidate = Path(candidate_dir) / filename
    candidate_relpath = str(candidate)
    if (REPO / candidate_relpath).exists():
        return candidate_relpath

    target_dir = REPO / candidate_dir
    fallback = _find_fuzzy_name_match(target_dir, filename)
    if fallback is not None:
        return str(fallback)

    return candidate_relpath


def _normalize_filename(name: str) -> str:
    normalized = name.lower().replace("’", "'")
    normalized = normalized.replace("hon.ble", "honble").replace("hon'ble", "honble").replace("honourable", "honble")
    normalized = normalized.replace("-", " ").replace("_", " ")
    normalized = re.sub(r"\b\d{4}\b", "", normalized)
    normalized = re.sub(r"\d{4}-\d{2}", "", normalized)
    normalized = re.sub(r"[\(\)]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _filename_tokens(name: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(r"[a-z]+", name.lower())
        if len(token) >= 3 and token not in {"the", "and", "for", "on", "at", "of", "to", "pdf", "in"}
    )


@lru_cache(maxsize=256)
def _extract_pdf_title_signature(pdf_path: Path) -> frozenset[str]:
    try:
        completed = subprocess.run(
            [
                "pdftotext",
                "-f",
                "1",
                "-l",
                "2",
                "-layout",
                str(pdf_path),
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return frozenset()

    return _filename_tokens(completed.stdout)


def _find_fuzzy_name_match(target_dir: Path, filename: str) -> Path | None:
    if not target_dir.exists() or not target_dir.is_dir():
        return None

    normalized_target = _normalize_filename(filename)
    target_tokens = _filename_tokens(normalized_target)
    if not target_tokens:
        return None

    target_signature = target_tokens
    best_score = 0.0
    best_title_score = 0.0
    best_file: Path | None = None
    files = [entry for entry in target_dir.iterdir() if entry.suffix.lower() == ".pdf" and entry.is_file()]
    for entry in files:
        normalized_candidate = _normalize_filename(entry.name)
        candidate_tokens = _filename_tokens(normalized_candidate)
        if not candidate_tokens:
            continue

        overlap = len(target_tokens & candidate_tokens) / len(target_tokens)
        if overlap < 0.45:
            continue

        ratio = SequenceMatcher(None, normalized_target, normalized_candidate).ratio()
        filename_score = overlap * 0.75 + ratio * 0.25
        title_signature = _extract_pdf_title_signature(entry)
        title_score = len(target_signature & title_signature) / len(target_signature) if target_signature else 0.0
        combined = filename_score
        if title_signature:
            combined = max(combined, filename_score * 0.55 + title_score * 0.45)
        if combined > best_score:
            best_score = combined
            best_file = entry
            best_title_score = title_score

    if best_file is not None and best_score >= 0.55:
        return best_file

    if best_title_score < 0.45:
        return None

    return best_file


def _clone_rajasthan_profiles(
    profiles: tuple[BudgetDocumentProfile, ...],
    *,
    target_fy: str,
    filename_overrides: dict[str, str] | None = None,
) -> tuple[BudgetDocumentProfile, ...]:
    cloned_profiles: list[BudgetDocumentProfile] = []
    for profile in profiles:
        source_relpath = _resolve_rajasthan_year_source(
            profile.source_relpath,
            target_fy,
            filename_overrides=filename_overrides,
        )
        if source_relpath is None:
            continue

        windows = []
        for window in profile.windows:
            window_source_relpath = _resolve_rajasthan_year_source(
                window.source_relpath,
                target_fy,
                filename_overrides=filename_overrides,
            )
            if window_source_relpath is None:
                continue
            windows.append(replace(window, source_relpath=window_source_relpath))

        cloned_profiles.append(
            replace(
                profile,
                fy=target_fy,
                source_relpath=source_relpath,
                windows=tuple(windows),
            )
        )
    return tuple(cloned_profiles)


RAJASTHAN_2023_24_DOCUMENTS = _clone_rajasthan_profiles(
    RAJASTHAN_2025_26_DOCUMENTS,
    target_fy="2023-24",
    filename_overrides=RAJASTHAN_FY_FILENAME_OVERRIDES["2023-24"],
)


RAJASTHAN_2022_23_DOCUMENTS = _clone_rajasthan_profiles(
    RAJASTHAN_2025_26_DOCUMENTS,
    target_fy="2022-23",
    filename_overrides=RAJASTHAN_FY_FILENAME_OVERRIDES["2022-23"],
)


def _rajasthan_doc_for_year(
    fy: str,
    document_type: str,
    filename: str,
    document_family: str,
    *,
    can_extract_be_re: bool,
    can_extract_codes: bool,
    can_extract_scheme_info: bool,
    parser_strategy: str,
    parser_unit: str = "lakh",
    code_axis: str = "none",
    amount_columns: str = "varies",
    notes: tuple[str, ...] = (),
) -> BudgetDocumentProfile:
    return replace(
        _rajasthan_doc(
            document_type,
            filename,
            document_family,
            can_extract_be_re=can_extract_be_re,
            can_extract_codes=can_extract_codes,
            can_extract_scheme_info=can_extract_scheme_info,
            parser_strategy=parser_strategy,
            parser_unit=parser_unit,
            code_axis=code_axis,
            amount_columns=amount_columns,
            notes=notes,
        ),
        fy=fy,
        source_relpath=f"data/state_budgets/Rajasthan/{fy}/State Budget/{filename}",
    )


RAJASTHAN_2024_25_DOCUMENTS = _clone_rajasthan_profiles(
    RAJASTHAN_2025_26_DOCUMENTS,
    target_fy="2024-25",
    filename_overrides=RAJASTHAN_FY_FILENAME_OVERRIDES["2024-25"],
) + (
    _rajasthan_doc_for_year(
        "2024-25",
        "budget_statement_vote_on_account",
        "Budget Statement 2024-2025 (08.02.2024).pdf",
        "speech",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="speech_text",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
    _rajasthan_doc_for_year(
        "2024-25",
        "budget_statement_vote_on_account_english",
        "Budget Statement 2024-2025 (08.02.2024) (English Version).pdf",
        "speech",
        can_extract_be_re=False,
        can_extract_codes=False,
        can_extract_scheme_info=True,
        parser_strategy="speech_text",
        parser_unit="mixed",
        code_axis="none",
        amount_columns="quoted_announcements",
    ),
)


RAJASTHAN_YEAR_DOCUMENTS = {
    "2013-14": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2013-14"),
    "2014-15": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2014-15"),
    "2015-16": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2015-16"),
    "2016-17": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2016-17"),
    "2017-18": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2017-18"),
    "2018-19": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2018-19"),
    "2019-20": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2019-20"),
    "2020-21": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2020-21"),
    "2021-22": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2021-22"),
    "2022-23": RAJASTHAN_2022_23_DOCUMENTS,
    "2023-24": RAJASTHAN_2023_24_DOCUMENTS,
    "2024-25": RAJASTHAN_2024_25_DOCUMENTS,
    "2025-26": RAJASTHAN_2025_26_DOCUMENTS,
    "2026-27": _clone_rajasthan_profiles(RAJASTHAN_2025_26_DOCUMENTS, target_fy="2026-27"),
}

DOCUMENT_PROFILES = {
    (profile.state.lower(), profile.fy, profile.document_type): profile
    for profiles in RAJASTHAN_YEAR_DOCUMENTS.values()
    for profile in profiles
}


def _normalize_state(state: str) -> str:
    return state.strip().lower()


def _normalize_text_filter(value: str | Sequence[str] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    return tuple(str(item).strip() for item in value if str(item).strip())


def document_profile_for(state: str, fy: str, document_type: str) -> BudgetDocumentProfile:
    try:
        return DOCUMENT_PROFILES[(_normalize_state(state), fy, document_type)]
    except KeyError as exc:
        raise KeyError(f"No budget document profile for {state} {fy} {document_type}") from exc


def document_profiles_for_state(
    state: str,
    fy: str,
    *,
    document_families: str | Sequence[str] | None = None,
    document_types: str | Sequence[str] | None = None,
    require_be_re: bool | None = None,
    require_codes: bool | None = None,
    require_scheme_info: bool | None = None,
) -> tuple[BudgetDocumentProfile, ...]:
    families = _normalize_text_filter(document_families)
    types = _normalize_text_filter(document_types)
    return tuple(
        profile
        for (profile_state, profile_fy, _), profile in DOCUMENT_PROFILES.items()
        if profile_state == _normalize_state(state)
        and profile_fy == fy
        and (families is None or profile.document_family in families)
        and (types is None or profile.document_type in types)
        and (require_be_re is None or profile.can_extract_be_re == require_be_re)
        and (require_codes is None or profile.can_extract_codes == require_codes)
        and (require_scheme_info is None or profile.can_extract_scheme_info == require_scheme_info)
    )


def document_profiles_for_intent(
    state: str,
    fy: str,
    *,
    intent: str,
    document_families: str | Sequence[str] | None = None,
) -> tuple[BudgetDocumentProfile, ...]:
    if intent == "be_re":
        return document_profiles_for_state(state, fy, document_families=document_families, require_be_re=True)
    if intent == "codes":
        return document_profiles_for_state(state, fy, document_families=document_families, require_codes=True)
    if intent == "scheme_info":
        return document_profiles_for_state(state, fy, document_families=document_families, require_scheme_info=True)
    raise ValueError(
        "intent must be one of: 'be_re', 'codes', 'scheme_info'"
    )


def document_profiles_for_dispatch(
    state: str,
    fy: str,
    *,
    intent: str | None = None,
    document_families: str | Sequence[str] | None = None,
    require_be_re: bool | None = None,
    require_codes: bool | None = None,
    require_scheme_info: bool | None = None,
) -> tuple[BudgetDocumentProfile, ...]:
    if intent:
        return document_profiles_for_intent(
            state,
            fy,
            intent=intent,
            document_families=document_families,
        )
    return document_profiles_for_state(
        state,
        fy,
        document_families=document_families,
        require_be_re=require_be_re,
        require_codes=require_codes,
        require_scheme_info=require_scheme_info,
    )


def state_profile_summary(state: str, fy: str) -> dict[str, object]:
    profiles = document_profiles_for_state(state, fy)
    families = sorted({profile.document_family for profile in profiles})
    return {
        "state": state,
        "fy": fy,
        "document_count": len(profiles),
        "families": families,
        "supports_be_re": sorted(profile.document_type for profile in profiles if profile.can_extract_be_re),
        "supports_codes": sorted(profile.document_type for profile in profiles if profile.can_extract_codes),
        "supports_scheme_info": sorted(profile.document_type for profile in profiles if profile.can_extract_scheme_info),
    }
