def generate_executive_summary(
    company_name,
    readiness_score,
    indicator_analysis
):
    """
    indicator_analysis: list of dicts
    [
        {
            "indicator": str,
            "status": "Reported" | "Partial" | "Not Reported",
            "coverage": int
        }
    ]
    """

    total = len(indicator_analysis)
    reported = len([i for i in indicator_analysis if i["status"] == "Reported"])
    partial = len([i for i in indicator_analysis if i["status"] == "Partial"])
    not_reported = len([i for i in indicator_analysis if i["status"] == "Not Reported"])

    summary = []

    # =========================
    # Overall statement
    # =========================
    summary.append(
        f"**{company_name}** achieved a **GRI Readiness Score of {readiness_score}%**, "
        f"indicating a {'strong' if readiness_score >= 75 else 'moderate' if readiness_score >= 50 else 'low'} "
        "level of sustainability reporting maturity."
    )

    # =========================
    # Strengths
    # =========================
    if reported > 0:
        summary.append(
            f"The company demonstrates strong disclosure practices with **{reported} indicators fully reported**, "
            "reflecting established data collection processes in key ESG areas."
        )

    # =========================
    # Gaps
    # =========================
    if not_reported > 0:
        summary.append(
            f"However, **{not_reported} indicators are not reported**, "
            "representing critical gaps that may affect transparency and stakeholder confidence."
        )

    if partial > 0:
        summary.append(
            f"In addition, **{partial} indicators are partially reported**, "
            "suggesting data quality or historical coverage limitations."
        )

    # =========================
    # Recommendations
    # =========================
    summary.append(
        "It is recommended to prioritize the closure of non-reported indicators, "
        "followed by improving data completeness for partially reported metrics. "
        "Strengthening governance and data management systems will significantly enhance future GRI readiness."
    )

    return summary
