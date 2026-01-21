def generate_executive_summary(company_name, readiness_score, indicator_analysis):
    total = len(indicator_analysis)
    reported = len([i for i in indicator_analysis if i["status"] == "Reported"])
    partial = len([i for i in indicator_analysis if i["status"] == "Partial"])
    not_reported = len([i for i in indicator_analysis if i["status"] == "Not Reported"])

    summary = []

    summary.append(
        f"{company_name} achieved a GRI Readiness Score of {readiness_score}%, "
        f"indicating a {'strong' if readiness_score >= 75 else 'moderate' if readiness_score >= 50 else 'low'} "
        "level of sustainability reporting maturity."
    )

    if reported:
        summary.append(
            f"The company fully reported {reported} indicators, reflecting established ESG data practices."
        )

    if not_reported:
        summary.append(
            f"{not_reported} indicators are not reported, representing critical disclosure gaps."
        )

    if partial:
        summary.append(
            f"{partial} indicators are partially reported, indicating data completeness challenges."
        )

    summary.append(
        "Priority actions include closing non-reported indicators and improving data quality "
        "for partially reported metrics to enhance overall GRI readiness."
    )

    return summary
