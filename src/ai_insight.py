def generate_ai_insight(company_name, indicator_analysis):
    """
    indicator_analysis: list of dicts
    each dict = {
        'indicator': str,
        'status': str,
        'coverage': int
    }
    """

    not_reported = [i for i in indicator_analysis if i["status"] == "Not Reported"]
    partial = [i for i in indicator_analysis if i["status"] == "Partial"]

    insights = []

    # 🔴 Critical gaps
    if not_reported:
        insights.append(
            f"❗ {company_name} has {len(not_reported)} indicators not reported, "
            "which significantly impacts GRI readiness and transparency."
        )

    # 🟡 Data quality issues
    if partial:
        insights.append(
            f"⚠️ {company_name} shows partial reporting in {len(partial)} indicators, "
            "indicating gaps in data collection or consistency."
        )

    # 🎯 Recommendations
    if not_reported:
        insights.append(
            "🔧 Priority action: initiate data collection for non-reported indicators, "
            "starting with high-impact ESG areas (Energy, Emissions, Water)."
        )

    if partial:
        insights.append(
            "📈 Improvement action: enhance data completeness and historical coverage "
            "to move indicators from Partial to Reported."
        )

    if not insights:
        insights.append(
            f"✅ {company_name} demonstrates strong GRI readiness with complete and consistent reporting."
        )

    return insights
