"""AI Insights Module - Weekly digests and anomaly explanations."""
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import anthropic


def get_transactions_for_period(start_date: date, end_date: date) -> List[Dict]:
    """Get transactions for a date range."""
    try:
        from .sheets_sync import get_all_transactions
        all_transactions = get_all_transactions()
        filtered = []
        for tx in all_transactions:
            tx_date_str = tx.get("Date", "")
            try:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d").date()
                if start_date <= tx_date <= end_date:
                    filtered.append(tx)
            except ValueError:
                continue
        return filtered
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []


def call_claude_for_digest(transactions: List[Dict], week_start: date, week_end: date) -> Dict:
    """Call Claude to generate weekly digest."""
    client = anthropic.Anthropic()
    total_spent = sum(abs(t.get("Amount", 0)) for t in transactions if t.get("Amount", 0) < 0)
    total_income = sum(t.get("Amount", 0) for t in transactions if t.get("Amount", 0) > 0)
    tx_count = len(transactions)

    by_category = {}
    for tx in transactions:
        cat = tx.get("Category", "Other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tx)

    category_summary = "\n".join([
        f"- {cat}: HK${sum(abs(t.get('Amount', 0)) for t in txs if t.get('Amount', 0) < 0):,.0f} ({len(txs)} transactions)"
        for cat, txs in sorted(by_category.items(), key=lambda x: sum(abs(t.get('Amount', 0)) for t in x[1]), reverse=True)
    ])

    prompt = f"""Analyze this week's spending data.
Week: {week_start} to {week_end}
Total Transactions: {tx_count}
Total Spent: HK${total_spent:,.0f}
Total Income: HK${total_income:,.0f}

Spending by Category:
{category_summary}

Return JSON:
{{"summary": "1-2 sentence overview", "highlights": ["3-4 key observations"], "recommendations": ["1-2 suggestions"], "unusual_patterns": ["any unusual activity"]}}"""

    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
    response_text = message.content[0].text
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text
    return json.loads(json_str.strip())


def generate_weekly_digest(week_start: date, week_end: date) -> Dict:
    """Generate AI-powered weekly spending analysis."""
    transactions = get_transactions_for_period(week_start, week_end)
    if not transactions:
        return {"summary": f"No transactions found for week of {week_start}", "highlights": [], "recommendations": [], "unusual_patterns": [], "week_start": str(week_start), "week_end": str(week_end), "transaction_count": 0}
    try:
        digest = call_claude_for_digest(transactions, week_start, week_end)
        digest["week_start"] = str(week_start)
        digest["week_end"] = str(week_end)
        digest["transaction_count"] = len(transactions)
        digest["generated_at"] = datetime.now().isoformat()
        return digest
    except Exception as e:
        return {"error": str(e), "week_start": str(week_start), "week_end": str(week_end)}


def call_claude_for_explanation(category: str, current: float, average: float, transactions: List[Dict]) -> str:
    """Call Claude to explain an anomaly."""
    client = anthropic.Anthropic()
    cat_transactions = [t for t in transactions if t.get("Category") == category]
    cat_transactions.sort(key=lambda x: abs(x.get("Amount", 0)), reverse=True)
    top_txns = cat_transactions[:5]
    txn_details = "\n".join([f"- {t.get('Merchant', t.get('Description', 'Unknown'))}: HK${abs(t.get('Amount', 0)):,.0f}" for t in top_txns])
    pct_change = ((current - average) / average) * 100 if average > 0 else 0
    prompt = f"""Explain this spending anomaly in 1-2 sentences:
Category: {category}
This month: HK${current:,.0f}
Average: HK${average:,.0f}
Change: {pct_change:+.0f}%
Top transactions:
{txn_details}
Be specific. Keep it brief."""
    message = client.messages.create(model="claude-sonnet-4-6", max_tokens=200, messages=[{"role": "user", "content": prompt}])
    return message.content[0].text


def explain_anomaly(category: str, current: float, average: float, transactions: List[Dict]) -> str:
    """Generate natural language explanation for a spending spike."""
    try:
        return call_claude_for_explanation(category, current, average, transactions)
    except Exception as e:
        pct_change = ((current - average) / average) * 100 if average > 0 else 0
        return f"{category} spending is {pct_change:+.0f}% compared to average."


def save_weekly_digest(digest: Dict) -> bool:
    """Save weekly digest to Google Sheets."""
    try:
        from .sheets_sync import save_insight_to_sheet
        return save_insight_to_sheet(digest)
    except Exception as e:
        print(f"Error saving digest: {e}")
        return False
