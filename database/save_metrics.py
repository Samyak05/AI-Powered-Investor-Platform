from sqlalchemy import text

from database.postgres_sql import get_engine


def _to_text_list(value):
    """
    Convert a value into a list of strings.

    Handles:
    - None
    - a single string
    - list / tuple / set
    - other values

    This prevents errors such as:
        TypeError: can only join an iterable
    """
    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]

    return [str(value)]


def save_metrics(
    company: str,
    year: int,
    metrics: dict
) -> None:
    """
    Save extracted financial metrics to PostgreSQL.

    Args:
        company: Company name.
        year: Fiscal year.
        metrics: Extracted KPI dictionary.
    """

    engine = get_engine()

    query = """
    INSERT INTO financial_metrics (
        company,
        year,
        revenue,
        net_income,
        operating_income,
        cash_flow,
        total_assets,
        total_liabilities,
        risk_factors,
        growth_drivers
    )
    VALUES (
        :company,
        :year,
        :revenue,
        :net_income,
        :operating_income,
        :cash_flow,
        :total_assets,
        :total_liabilities,
        :risk_factors,
        :growth_drivers
    )
    """

    # ---------------------------------------------------------
    # Support both Pydantic model_dump() keys and older aliases
    # ---------------------------------------------------------

    revenue = (
        metrics.get("revenue")
        or metrics.get("Revenue")
    )

    net_income = (
        metrics.get("net_income")
        or metrics.get("Net Income")
    )

    operating_income = (
        metrics.get("operating_income")
        or metrics.get("Operating Income")
    )

    cash_flow = (
        metrics.get("cash_flow")
        or metrics.get("Cash Flow from Operating Activities")
    )

    total_assets = (
        metrics.get("total_assets")
        or metrics.get("Total Assets")
    )

    total_liabilities = (
        metrics.get("total_liabilities")
        or metrics.get("Total Liabilities")
    )

    risk_factors = (
        metrics.get("risk_factors")
        or metrics.get("Top Risk Factors")
    )

    growth_drivers = (
        metrics.get("growth_drivers")
        or metrics.get("Top Growth Drivers")
    )

    # ---------------------------------------------------------
    # Normalize list-based fields
    # ---------------------------------------------------------

    risk_factors = _to_text_list(risk_factors)
    growth_drivers = _to_text_list(growth_drivers)

    # ---------------------------------------------------------
    # Prepare PostgreSQL parameters
    # ---------------------------------------------------------

    params = {
        "company": company,
        "year": year,
        "revenue": revenue,
        "net_income": net_income,
        "operating_income": operating_income,
        "cash_flow": cash_flow,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "risk_factors": "\n".join(risk_factors),
        "growth_drivers": "\n".join(growth_drivers),
    }

    # ---------------------------------------------------------
    # Insert into PostgreSQL
    # ---------------------------------------------------------

    with engine.begin() as connection:
        connection.execute(text(query), params)

    print(
        f"Successfully saved metrics for {company} {year}"
    )


# -------------------------------------------------------------
# Standalone test
# -------------------------------------------------------------

if __name__ == "__main__":

    sample_metrics = {
        "Revenue": "$391,035",
        "Net Income": "$93,736",
        "Operating Income": "$123,216",
        "Cash Flow from Operating Activities": "$118,254",
        "Total Assets": "$364,980",
        "Total Liabilities": "$308,030",

        "Top Risk Factors": [
            "Macroeconomic conditions including inflation, interest rates, and currency fluctuations could materially impact results.",
            "High competition with aggressive pricing, short product life cycles, and rapid technological changes.",
            "Dependence on single or limited sources for certain components, with potential supply shortages.",
            "Exposure to foreign exchange rate fluctuations impacting sales and margins.",
            "Legal and regulatory challenges, including significant tax disputes such as the State Aid Decision.",
        ],

        "Top Growth Drivers": [
            "Increased Services revenue from advertising, App Store, and cloud services.",
            "Higher Mac sales driven by increased laptop demand.",
            "Continued strong iPhone sales performance.",
            "Continued strong iPhone sales performance.",
            "Strong cash generation enabling capital returns and strategic investment.",
        ],
    }

    save_metrics(
        company="Apple",
        year=2024,
        metrics=sample_metrics,
    )