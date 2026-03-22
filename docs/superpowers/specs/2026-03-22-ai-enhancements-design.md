# Finance Tracker AI Enhancements Design

**Date:** 2026-03-22
**Status:** Draft
**Author:** Claude (with user input)

## Overview

Enhance the Finance Tracker with 6 AI-powered features to improve categorization accuracy, support more document types, provide intelligent insights, and handle multi-currency transactions.

## Requirements Summary

| Feature | Requirement |
|---------|-------------|
| ML Categorization | Learn from dashboard edits only |
| OCR | Scanned bank statements + receipt photos |
| AI Insights | Weekly digest reports |
| Forecasting | 3-month spending outlook |
| Anomaly Explanations | AI-powered explanations |
| Multi-currency | HKD as base currency |

## Architecture

### Approach: Claude-Centric

All AI functionality uses the Claude API for consistency and simplicity. This keeps the codebase clean and leverages Claude's multimodal capabilities (text + vision).

```
┌──────────────────────────────────────────────────────────────────┐
│                     Finance Tracker AI                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   Input     │    │  AI Core    │    │   Output    │          │
│  │  Sources    │───▶│  (Claude)   │───▶│  & Storage  │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│        │                  │                   │                  │
│        ▼                  ▼                   ▼                  │
│  • Text PDFs        • parser.py          • Google Sheets        │
│  • Scanned PDFs     • ai_insights.py     • Dashboard            │
│  • Receipt Photos   • forecaster.py      • Weekly Digests       │
│  • Dashboard edits  • learning.py                               │
│                     • fx_converter.py                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### New Files

| File | Purpose |
|------|---------|
| `src/ai_insights.py` | Weekly digest generation, anomaly explanations |
| `src/forecaster.py` | 3-month spending projections using historical patterns |
| `src/learning.py` | Categorization learning from user corrections |
| `src/fx_converter.py` | Multi-currency FX conversion using free API |
| `src/ocr.py` | Image/scanned PDF processing via Claude Vision |
| `scripts/weekly_digest.py` | Cron job for weekly insight generation |

### Modified Files

| File | Changes |
|------|---------|
| `src/parser.py` | Add vision support, integrate learning context |
| `src/sheets_sync.py` | New sheets: Learning Rules, Insights, FX Rates |
| `dashboard/app.py` | Learning capture, insights display, forecasts, FX |
| `requirements.txt` | Add any new dependencies |

## Data Model

### New Google Sheets

#### Learning Rules Sheet

Stores user corrections for in-context learning.

| Column | Type | Description |
|--------|------|-------------|
| Merchant Pattern | string | Original merchant text or regex pattern |
| Description Pattern | string | Transaction description pattern |
| Original Category | string | What AI originally assigned |
| Corrected Category | string | What user changed it to |
| Confidence | number | Times this correction has been applied |
| Created At | datetime | When first corrected |
| Last Used | datetime | When last matched in parsing |
| Version | number | Increment on each update to same pattern |
| Active | boolean | Whether this rule is currently active |

**Learning Rule Conflict Resolution:**
- If same merchant pattern gets corrected to different categories over time:
  - Keep historical record (version increments)
  - Most recent correction (highest version) wins
  - Rules only applied when Confidence >= 2 (prevents one-off mistakes from becoming rules)
  - Dashboard shows "conflicting rules" warning if pattern has multiple categories

#### Insights Sheet

Stores generated weekly digests and forecasts.

| Column | Type | Description |
|--------|------|-------------|
| Week Start | date | Week start date (Monday) |
| Week End | date | Week end date (Sunday) |
| Digest | text | AI-generated weekly narrative |
| Top Insights | text | JSON array of key findings |
| Forecast 3M | text | JSON with 3-month projections |
| Anomalies | text | JSON with explained anomalies |
| Generated At | datetime | When generated |

#### FX Rates Sheet

Caches exchange rates for multi-currency conversion.

| Column | Type | Description |
|--------|------|-------------|
| Date | date | Rate date |
| From Currency | string | Source currency code (USD, CNY, EUR, etc.) |
| To HKD Rate | number | Conversion rate to HKD |
| Source | string | API source (frankfurter.app) |

### Modified Transactions Sheet

Add columns for multi-currency support:

| New Column | Type | Description |
|------------|------|-------------|
| Original Currency | string | Currency as stated in transaction |
| Original Amount | number | Amount in original currency |
| FX Rate | number | Exchange rate used |
| HKD Amount | number | Converted amount in HKD |

## Feature Specifications

### 1. ML Categorization Learning

**Goal:** Learn from user corrections to improve future categorization accuracy.

**Flow:**
1. User edits a transaction category in the dashboard
2. System detects the change (old category vs new category)
3. Stores correction pattern in Learning Rules sheet
4. Future parsing prompts include top 50 learned rules as examples
5. AI uses these examples for better categorization

**Implementation Details:**

`learning.py`:
```python
def capture_correction(transaction_id: str, old_category: str, new_category: str):
    """Store a category correction for learning."""

def get_learning_context(limit: int = 50) -> str:
    """Build prompt context from top corrections."""

def match_learned_rules(merchant: str, description: str) -> Optional[str]:
    """Check if transaction matches any learned rules."""
```

**Parser Integration:**
- Inject learning context into the categorization prompt
- Format: "Based on past corrections: 'UBER EATS*' should be 'Dining' not 'Transportation'"

### 2. OCR for Scanned Documents

**Goal:** Support scanned PDFs and receipt photos using Claude Vision.

**Flow:**
1. Detect if PDF is scanned (no extractable text) or if input is an image
2. Send to Claude Vision API for text extraction
3. Parse extracted content through standard transaction parser

**Implementation Details:**

`ocr.py`:
```python
def is_scanned_pdf(pdf_path: Path) -> bool:
    """Check if PDF has extractable text or is image-based."""

def process_image(image_path: Path) -> dict:
    """Process receipt photo, extract transaction data."""

def process_scanned_pdf(pdf_path: Path) -> str:
    """Extract text from scanned PDF using Claude Vision."""
```

**Supported Formats:**
- Scanned PDF bank statements
- Receipt photos (JPEG, PNG, HEIC via pillow-heif)
- Screenshots of digital receipts

**Image Constraints:**
- Max file size: 10MB
- Recommended resolution: 1000-3000px on longest side
- HEIC files auto-converted to JPEG before Claude API call

**OCR Error Handling:**
| Scenario | Handling |
|----------|----------|
| Vision extracts no text | Return `{"error": "no_text_extracted", "needs_manual_review": true}` |
| Vision extracts partial text | Parse what's available, flag as `low_confidence` |
| Image too blurry/dark | Return `{"error": "image_quality", "suggestion": "Retake photo with better lighting"}` |
| Unsupported format | Convert if possible, else reject with format error |

**Receipt Extraction:**
```json
{
  "merchant": "Starbucks",
  "date": "2026-03-22",
  "total": 45.00,
  "currency": "HKD",
  "items": [
    {"name": "Latte", "price": 38.00},
    {"name": "Croissant", "price": 7.00}
  ]
}
```

### 3. AI Spending Insights (Weekly Digests)

**Goal:** Generate intelligent weekly spending summaries with actionable insights.

**Flow:**
1. Cron job runs Sunday 9am
2. Gather all transactions from the past week
3. Send to Claude for analysis
4. Store digest in Insights sheet
5. Display in dashboard "Insights" tab

**Implementation Details:**

`ai_insights.py`:
```python
def generate_weekly_digest(week_start: date, week_end: date) -> dict:
    """Generate AI-powered weekly spending analysis."""

def explain_anomaly(category: str, current: float, average: float,
                    transactions: list) -> str:
    """Generate natural language explanation for spending spike."""
```

**Digest Structure:**
```json
{
  "summary": "This week you spent HK$12,450 across 47 transactions, 8% below your monthly average.",
  "highlights": [
    "Dining spending dropped 25% - great progress!",
    "New subscription detected: Netflix HK$78/month",
    "Largest single purchase: Apple Store HK$7,899"
  ],
  "recommendations": [
    "Consider reviewing your 5 active subscriptions totaling HK$450/month",
    "Transportation costs could be reduced with monthly Octopus auto-top-up"
  ],
  "unusual_patterns": [
    "3 ATM withdrawals totaling HK$3,000 - unusually high cash usage"
  ]
}
```

**Cron Setup (macOS launchd):**

Create `~/Library/LaunchAgents/com.finance-tracker.weekly-digest.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.finance-tracker.weekly-digest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/sudhanshu.mohanty/finance-tracker/scripts/weekly_digest.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/sudhanshu.mohanty/finance-tracker/logs/digest.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/sudhanshu.mohanty/finance-tracker/logs/digest_error.log</string>
</dict>
</plist>
```

**Timezone:** Hong Kong Time (HKT, UTC+8). The script uses system timezone.

### 4. Spending Forecasting

**Goal:** Project spending trends for the next 3 months.

**Flow:**
1. Analyze 6-12 months of historical data (minimum 3 months required)
2. Identify trends, seasonality, recurring expenses
3. Project forward with confidence intervals
4. Display in dashboard with charts

**Confidence Level Criteria:**
| Level | Criteria |
|-------|----------|
| High | 6+ months data, low variance (<15% month-to-month), consistent patterns |
| Medium | 3-6 months data, moderate variance (15-30%), some patterns identified |
| Low | <3 months data, high variance (>30%), or significant anomalies in recent data |

**Sparse Data Handling:**
- < 1 month: No forecast generated, show "Need more data" message
- 1-3 months: Generate simple projection based on average, confidence = "low"
- 3-6 months: Generate trend-based forecast, confidence = "medium"
- 6+ months: Full forecast with seasonality, confidence varies by variance

**Implementation Details:**

`forecaster.py`:
```python
def generate_forecast(months_ahead: int = 3) -> dict:
    """Generate spending forecast using historical patterns."""

def identify_trends(transactions: list) -> dict:
    """Identify spending trends by category."""

def detect_seasonality(transactions: list) -> dict:
    """Detect seasonal patterns (holidays, etc.)."""
```

**Forecast Output:**
```json
{
  "forecast_months": [
    {
      "month": "2026-04",
      "projected_total": 45000,
      "confidence": "high",
      "by_category": {
        "Dining & Restaurants": 8500,
        "Transportation": 3200,
        "Shopping": 12000
      }
    }
  ],
  "trends": {
    "overall": "Spending trending up 5% month-over-month",
    "categories": {
      "Dining": "Decreasing trend (-10% past 3 months)",
      "Shopping": "Increasing trend (+15% past 3 months)"
    }
  },
  "seasonality_notes": "June typically 20% higher due to summer activities"
}
```

### 5. AI Anomaly Explanations

**Goal:** Provide intelligent explanations for spending spikes, not just detection.

**Flow:**
1. Detect anomaly using existing threshold logic
2. Gather transactions causing the spike
3. Send to Claude for contextual analysis
4. Display explanation in dashboard alert

**Implementation Details:**

Enhance `dashboard/app.py`:
```python
def explain_anomaly(category: str, current: float, average: float,
                    transactions: pd.DataFrame) -> str:
    """Get AI explanation for spending anomaly."""
```

**Example Explanations:**
- "Dining is 45% above average. This is driven by 3 large group dinners at high-end restaurants (Amber HK$1,200, Lung King Heen HK$980, Caprice HK$1,500)."
- "Shopping spike is due to a single HK$8,000 purchase at Apple Store - appears to be a one-time device purchase, not a trend change."

### 6. Multi-Currency FX Handling

**Goal:** Automatically convert foreign currency transactions to HKD.

**Flow:**
1. Parse currency from transaction (USD, EUR, CNY, etc.)
2. Fetch exchange rate for transaction date
3. Convert to HKD
4. Store both original and converted amounts

**Implementation Details:**

`fx_converter.py`:
```python
def get_fx_rate(from_currency: str, date: date) -> float:
    """Fetch exchange rate from API or cache."""

def convert_to_hkd(amount: float, currency: str, date: date) -> tuple:
    """Convert amount to HKD, return (hkd_amount, fx_rate)."""

def update_fx_cache():
    """Update cached FX rates for common currencies."""
```

**FX Rate Source:**
- Primary: frankfurter.app (free, no API key required)
- Fallback: exchangerate-api.com
- Cache rates daily in FX Rates sheet

**Rate Limiting & Caching:**
- frankfurter.app allows ~100 requests/day; cache aggressively
- Batch rate fetches: get all needed currencies in one call
- Pre-fetch common currencies (USD, EUR, CNY, GBP) daily
- On-demand fetch for uncommon currencies, then cache

**Stale Rate Policy:**
| Rate Age | Action |
|----------|--------|
| 0-3 days | Use cached rate normally |
| 4-7 days | Use cached rate, log warning, attempt API refresh |
| 8+ days | Flag transaction as "FX_RATE_STALE", use cached rate |
| API down | Use most recent rate regardless of age, flag all affected transactions |

If stale rate is used, add note to transaction: "FX rate from [date], may differ from actual conversion"

**Supported Currencies:**
- USD, EUR, GBP, CNY, JPY, SGD, AUD, CAD
- Additional currencies detected automatically

**Dashboard Display:**
- Show original amount with currency flag
- Show HKD equivalent
- Tooltip shows exchange rate used

## Dashboard Changes

### New "Insights" Tab

- Weekly digest display with expandable sections
- Historical insights archive
- 3-month forecast chart (area chart with confidence bands)
- Anomaly alerts with AI explanations

### Enhanced Transaction Table

- New columns: Original Currency, Original Amount, HKD Amount
- Currency filter dropdown
- Inline category editing (for learning capture)

### Forecast Chart

- Line/area chart showing projected spending
- By-category breakdown option
- Confidence interval shading

## Error Handling

| Scenario | Handling |
|----------|----------|
| FX API unavailable | Use cached rate per stale policy (see FX section) |
| Claude API error | Retry 3x with exponential backoff (1s, 2s, 4s), then skip |
| Claude Vision no text | Return structured error, flag for manual review |
| Claude Vision partial text | Parse available data, mark as `low_confidence` |
| Scanned PDF unreadable | Mark as "needs manual review" |
| Learning rules conflict | Use most recent correction with Confidence >= 2 |
| HEIC conversion fails | Return error with "Convert to JPEG and retry" suggestion |
| Weekly digest data empty | Skip generation, log warning, try again next week |
| Forecast insufficient data | Return "need more data" response, no forecast |

**Anomaly Explanation Caching:**
- Cache explanations in session (not persisted)
- Same anomaly viewed multiple times reuses cached explanation
- Cache invalidated when transaction data changes

## Testing Strategy

1. **Unit Tests:** Each new module (learning, ocr, forecaster, fx_converter, ai_insights)
2. **Integration Tests:** End-to-end parsing with learning, FX conversion pipeline
3. **Manual Testing:** Receipt photos, scanned PDFs from various banks

## Implementation Order

1. **Phase 1: Foundation** (fx_converter, learning infrastructure)
2. **Phase 2: OCR** (ocr.py, parser integration)
3. **Phase 3: Insights** (ai_insights, forecaster, weekly_digest)
4. **Phase 4: Dashboard** (all UI changes)
5. **Phase 5: Polish** (error handling, testing, documentation)

## Dependencies

**New Python packages:**
- `pillow-heif` - HEIC image support for iPhone receipt photos
- `Pillow` - Image processing (likely already installed)

**External Services:**
- Claude API (existing)
- frankfurter.app (free FX rates, no key required)

## Cost Estimate

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Claude API (additional) | ~$5-10 |
| FX API | Free |
| **Total** | **~$5-10/month** |

## Success Criteria

1. Categorization accuracy improves by 20%+ after 50 corrections
2. 90%+ of scanned PDFs successfully parsed
3. Weekly digests generated consistently
4. Forecasts within 20% of actual spending
5. All foreign transactions converted to HKD automatically
