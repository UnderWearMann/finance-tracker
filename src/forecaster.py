"""Forecaster Module - 3-month spending projections."""
import json
from datetime import date, datetime
from typing import Dict, List
import anthropic


def get_historical_data() -> List[Dict]:
    """Get monthly spending summaries."""
    try:
        from .sheets_sync import get_all_transactions
        transactions = get_all_transactions()
        by_month = {}
        for tx in transactions:
            tx_date_str = tx.get("Date", "")
            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d")
                month_key = tx_date.strftime("%Y-%m")
            except ValueError:
                continue
            if month_key not in by_month:
                by_month[month_key] = {"total": 0, "by_category": {}}
            amount = abs(tx.get("Amount", 0)) if tx.get("Amount", 0) < 0 else 0
            category = tx.get("Category", "Other")
            by_month[month_key]["total"] += amount
            if category not in by_month[month_key]["by_category"]:
                by_month[month_key]["by_category"][category] = 0
            by_month[month_key]["by_category"][category] += amount
        return [{"month": month, **data} for month, data in sorted(by_month.items())]
    except Exception as e:
        print(f"Error getting historical data: {e}")
        return []


def calculate_variance(monthly_totals: List[float]) -> float:
    """Calculate coefficient of variation."""
    if len(monthly_totals) < 2:
        return 1.0
    mean = sum(monthly_totals) / len(monthly_totals)
    if mean == 0:
        return 1.0
    variance = sum((x - mean) ** 2 for x in monthly_totals) / len(monthly_totals)
    return (variance ** 0.5) / mean


def calculate_confidence_level(months: int, variance: float) -> str:
    """Calculate forecast confidence: high/medium/low."""
    if months < 3 or variance > 0.30:
        return "low"
    elif months >= 6 and variance < 0.15:
        return "high"
    else:
        return "medium"


def call_claude_for_forecast(historical: List[Dict], months_ahead: int) -> Dict:
    """Call Claude to generate forecast."""
    client = anthropic.Anthropic()
    history_summary = "\n".join([
        f"- {m['month']}: HK${m['total']:,.0f}" for m in historical[-12:]
    ])
    totals = [m["total"] for m in historical]
    variance = calculate_variance(totals)
    confidence = calculate_confidence_level(len(historical), variance)

    prompt = f"""Forecast next {months_ahead} months based on this history:
{history_summary}
Data points: {len(historical)} months, Variance: {variance:.1%}

Return JSON:
{{"forecast_months": [{{"month": "YYYY-MM", "projected_total": 45000, "confidence": "{confidence}", "by_category": {{}}}}], "trends": {{"overall": "Brief trend"}}, "seasonality_notes": ""}}"""

    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    response_text = message.content[0].text
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text
    return json.loads(json_str.strip())


def generate_forecast(months_ahead: int = 3) -> Dict:
    """Generate spending forecast."""
    historical = get_historical_data()
    if len(historical) < 1:
        return {"need_more_data": True, "message": "No historical data available.", "forecast_months": []}
    if len(historical) < 3:
        avg_total = sum(m["total"] for m in historical) / len(historical)
        last_month = datetime.strptime(historical[-1]["month"], "%Y-%m")
        forecast_months = []
        for i in range(1, months_ahead + 1):
            month = last_month.month + i
            year = last_month.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            forecast_months.append({"month": f"{year}-{month:02d}", "projected_total": round(avg_total, 0), "confidence": "low", "by_category": {}})
        return {"forecast_months": forecast_months, "trends": {"overall": "Insufficient data for trend analysis"}, "seasonality_notes": "", "data_months": len(historical), "generated_at": datetime.now().isoformat()}
    try:
        forecast = call_claude_for_forecast(historical, months_ahead)
        forecast["data_months"] = len(historical)
        forecast["generated_at"] = datetime.now().isoformat()
        return forecast
    except Exception as e:
        return {"error": str(e), "forecast_months": []}


def identify_trends(transactions: List[Dict]) -> Dict:
    """Identify spending trends by category."""
    historical = get_historical_data()
    if len(historical) < 3:
        return {"insufficient_data": True}
    trends = {}
    recent_3 = historical[-3:]
    all_categories = set()
    for m in historical:
        all_categories.update(m["by_category"].keys())
    for category in all_categories:
        amounts = [m["by_category"].get(category, 0) for m in recent_3]
        if amounts[0] == 0:
            continue
        change = (amounts[-1] - amounts[0]) / amounts[0] * 100
        if change > 10:
            trends[category] = f"Increasing (+{change:.0f}%)"
        elif change < -10:
            trends[category] = f"Decreasing ({change:.0f}%)"
        else:
            trends[category] = "Stable"
    return trends
