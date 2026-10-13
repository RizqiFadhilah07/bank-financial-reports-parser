import re

# --- PDF ---
TWO_COLUMN_BANKS = {"BTPN Syariah"}
SPLIT_X = 391.5

SECTION_WINDOW = 400

SECTION_ANCHORED_METRICS = {
    "other_commitment_receivables": "TAGIHAN KOMITMEN",
    "other_commitment_obligations": "KEWAJIBAN KOMITMEN",
    "other_accrued_income": "Pendapatan dalam penyelesaian",
    "other_contingent_receivables": "TAGIHAN KONTINJENSI",
    "other_contingent_obligations": "KEWAJIBAN KONTINJENSI",
    "other_non_reclassifiable_oci": "Pos-pos yang tidak akan direklasifikasi ke laba rugi",
    "other_reclassifiable_oci": "Pos-pos yang akan direklasifikasi ke laba rugi",
    "other_additional_paid_in_capital": "Tambahan modal disetor",
    "other_fund_distribution_income": "Pendapatan Sewa",
}

LETTERED_SUBITEM_FALLBACK = {
    "revaluation_gain_fixed_assets": ("Pos-pos yang tidak akan direklasifikasi ke laba rugi", 1, True),
    "remeasurement_defined_benefit_gain_loss": ("Pos-pos yang tidak akan direklasifikasi ke laba rugi", 2, True),
    "foreign_currency_translation_gain_loss": ("Pos-pos yang akan direklasifikasi ke laba rugi", 1, True),
    "fair_value_oci_gain_loss": ("Pos-pos yang akan direklasifikasi ke laba rugi", 2, True),
    "current_tax_expense": ("Pajak penghasilan", 1, False),
}


PURE_HEADER_METRICS = {
    "BSI": {"income_tax"},
}

DEFER_TO_FALLBACK_IF_EMPTY = {"current_tax_expense"}

SECTION_HEADER_METRICS = {
    "commitment_receivables", "commitment_payables",
    "contingent_receivables", "contingent_payables",
}


NEGATIVE_ALIASES = {
    "interest_expense", "personnel_expense", "promotion_expense",
    "other_operating_expense", "impairment_loss_recovery", "operational_risk_loss",
    "wadiah_bonus_expense", "other_non_financial_asset_impairment",
    "unpaid_capital", "treasury_stock", "dividends_paid",
    "other_comprehensive_income_loss", "impairment_allowance",
    "held_securities_impairment", "loans_and_sharia_financing_impairment",
    "other_asset_impairment", "accumulated_amortization_intangible_assets",
    "accumulated_depreciation_fixed_assets", "current_tax_expense",
    "share_discount", "istishna_progress_billing", "income_tax",
    "profit_distribution_to_investment_fund_owners",
    "non_profit_sharing_distribution", "profit_sharing_distribution",
}

TERM_VARIANTS = {
    "UOB": {
        "profit_before_tax": ["LABA (RUGI) PERIODE BERJALAN SEBELUM PAJAK"],
        "net_profit": ["LABA (RUGI) BERSIH PERIODE BERJALAN"],
        "other_comprehensive_income_after_tax": [
            "PENGHASILAN KOMPREHENSIF LAIN PERIODE BERJALAN SETELAH PAJAK"],
        "total_comprehensive_income": [
            "TOTAL LABA (RUGI) KOMPREHENSIF PERIODE BERJALAN"],
        "current_tax_expense": ["Taksiran pajak periode berjalan"],
    },
    "Mandiri": {
        "unused_credit_commitments": [
            "Fasilitas kredit/pembiayaan kepada nasabah yang belum ditarik"],
    },
}

NUMBER_RE = re.compile(r"\(?-?\d[\d.,]*\)?")
NEG_RE = re.compile(r"\b(beban|rugi|kerugian|biaya)\b", re.IGNORECASE)
POS_RE = re.compile(r"\b(laba|keuntungan|pendapatan|penghasilan)\b", re.IGNORECASE)
PAREN_NUM_RE = re.compile(r"\(\s*\d[\d.,]*\s*\)")