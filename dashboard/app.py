"""
Finance Tracker Dashboard
Interactive spending analysis with charts and insights
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import sys
from pathlib import Path
import json

# Add parent directory to path for importing learning module
sys.path.insert(0, str(Path(__file__).parent.parent))
from learning import capture_correction, capture_corrections_bulk
from sheets_sync import get_latest_insights
from forecaster import generate_forecast
from ai_insights import explain_anomaly

from sheets_sync import (
    get_all_transactions, get_account_info, get_categories,
    add_category, update_transaction_category, update_transaction_categories_bulk
)
from config import (
    DEFAULT_CATEGORIES, ANOMALY_THRESHOLD_PERCENT, STALENESS_DAYS,
    COLORS, CATEGORY_COLORS
)

# Page config
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS styling
st.markdown("""
<style>
    /* Base styles */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .metric-card h3 {
        color: #64748b;
        font-size: 0.875rem;
        font-weight: 500;
        margin: 0 0 8px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    .metric-card .value.positive { color: #04d38c; }
    .metric-card .value.negative { color: #ef4444; }
    .metric-card .trend {
        font-size: 0.875rem;
        color: #64748b;
        margin-top: 4px;
    }
    .metric-card .trend.up { color: #04d38c; }
    .metric-card .trend.down { color: #ef4444; }

    /* Quick stats bar */
    .stats-bar {
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
    }
    .stats-bar .stat-item {
        text-align: center;
        flex: 1;
        min-width: 120px;
    }
    .stats-bar .stat-label {
        color: rgba(255,255,255,0.8);
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .stats-bar .stat-value {
        color: white;
        font-size: 1.5rem;
        font-weight: 700;
    }

    /* Alert boxes */
    .alert-box {
        padding: 16px 20px;
        border-radius: 12px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .alert-warning {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
    }
    .alert-danger {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border-left: 4px solid #ef4444;
    }
    .alert-success {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 4px solid #04d38c;
    }
    .alert-info {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        border-left: 4px solid #1a73e8;
    }
    .alert-box .alert-icon {
        font-size: 1.25rem;
    }
    .alert-box .alert-content {
        flex: 1;
    }
    .alert-box .alert-title {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 2px;
    }
    .alert-box .alert-text {
        color: #64748b;
        font-size: 0.875rem;
    }

    /* Insight cards */
    .insight-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .insight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .insight-card .insight-icon {
        font-size: 1.5rem;
        margin-bottom: 8px;
    }
    .insight-card .insight-title {
        font-weight: 600;
        color: #1e293b;
        font-size: 0.875rem;
        margin-bottom: 4px;
    }
    .insight-card .insight-text {
        color: #64748b;
        font-size: 0.875rem;
        line-height: 1.5;
    }

    /* Category pills */
    .category-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
        color: white;
    }

    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e2e8f0;
    }
    .section-header h2 {
        color: #1e293b;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
    }

    /* Charts container */
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }

    /* Data table styling */
    .dataframe {
        border-radius: 8px !important;
        overflow: hidden;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8fafc;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Custom button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(26, 115, 232, 0.4);
    }

    /* Progress bar styling */
    .budget-progress {
        height: 8px;
        border-radius: 4px;
        background: #e2e8f0;
        overflow: hidden;
    }
    .budget-progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)


def get_category_color(category: str) -> str:
    """Get consistent color for a category."""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS.get("Other", "#64748b"))


@st.cache_data(ttl=300)
def load_data():
    """Load transaction data from Google Sheets."""
    try:
        transactions = get_all_transactions()
        accounts = get_account_info()
        return pd.DataFrame(transactions), pd.DataFrame(accounts)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data(ttl=300)
def load_categories():
    """Load categories from Google Sheets."""
    try:
        categories = get_categories()
        return categories if categories else DEFAULT_CATEGORIES
    except Exception:
        return DEFAULT_CATEGORIES


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare transaction data for analysis."""
    if df.empty:
        return df

    df = df.copy()

    # Convert date
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    # Convert amount to numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # Add derived columns
    df['Month'] = df['Date'].dt.to_period('M')
    df['MonthStr'] = df['Date'].dt.strftime('%Y-%m')
    df['Year'] = df['Date'].dt.year
    df['DayOfWeek'] = df['Date'].dt.day_name()

    # Separate income and expenses
    df['IsExpense'] = df['Amount'] < 0
    df['ExpenseAmount'] = df['Amount'].apply(lambda x: abs(x) if x < 0 else 0)
    df['IncomeAmount'] = df['Amount'].apply(lambda x: x if x > 0 else 0)

    # Check for CC payment flag
    if 'Is CC Payment' not in df.columns:
        df['Is CC Payment'] = False
    else:
        df['Is CC Payment'] = df['Is CC Payment'].fillna(False).astype(bool)

    return df


def check_staleness(accounts_df: pd.DataFrame) -> list:
    """Check for accounts with stale statements."""
    alerts = []
    if accounts_df.empty:
        return alerts

    today = datetime.now().date()
    threshold = today - timedelta(days=STALENESS_DAYS)

    for _, row in accounts_df.iterrows():
        try:
            last_date = pd.to_datetime(row.get('Last Statement Date', ''), errors='coerce')
            if pd.isna(last_date):
                continue
            if last_date.date() < threshold:
                days_old = (today - last_date.date()).days
                alerts.append({
                    'account': row.get('Account Name', 'Unknown'),
                    'days_old': days_old,
                    'last_date': last_date.strftime('%Y-%m-%d')
                })
        except Exception:
            continue

    return alerts


def detect_anomalies(df: pd.DataFrame) -> list:
    """Detect spending anomalies vs. historical averages."""
    anomalies = []
    if df.empty or len(df['MonthStr'].unique()) < 2:
        return anomalies

    current_month = df['MonthStr'].max()
    months = sorted(df['MonthStr'].unique())[-4:]

    if len(months) < 2:
        return anomalies

    current_data = df[df['MonthStr'] == current_month]
    historical = df[(df['MonthStr'].isin(months[:-1])) & (df['MonthStr'] != current_month)]

    if historical.empty:
        return anomalies

    hist_avg = historical.groupby('Category')['ExpenseAmount'].sum() / len(months[:-1])
    current_cat = current_data.groupby('Category')['ExpenseAmount'].sum()

    for category in current_cat.index:
        if category not in hist_avg.index or hist_avg[category] == 0:
            continue

        current_val = current_cat[category]
        avg_val = hist_avg[category]
        pct_change = ((current_val - avg_val) / avg_val) * 100

        if pct_change > ANOMALY_THRESHOLD_PERCENT:
            anomalies.append({
                'type': 'category',
                'name': category,
                'current': current_val,
                'average': avg_val,
                'pct_change': pct_change
            })

    anomalies.sort(key=lambda x: x['pct_change'], reverse=True)
    return anomalies[:5]


def generate_insights(df: pd.DataFrame) -> list:
    """Generate smart insights from transaction data."""
    insights = []
    if df.empty:
        return insights

    expenses = df[df['IsExpense']]
    if expenses.empty:
        return insights

    # Top spending category
    top_cat = expenses.groupby('Category')['ExpenseAmount'].sum().idxmax()
    top_cat_amount = expenses.groupby('Category')['ExpenseAmount'].sum().max()
    total_expenses = expenses['ExpenseAmount'].sum()
    top_cat_pct = (top_cat_amount / total_expenses * 100) if total_expenses > 0 else 0

    insights.append({
        'icon': '',
        'title': 'Top Spending Category',
        'text': f"<strong>{top_cat}</strong> accounts for {top_cat_pct:.0f}% of spending (${top_cat_amount:,.0f})"
    })

    # Subscription detection
    potential_subs = expenses[expenses['Category'] == 'Subscriptions']
    if not potential_subs.empty:
        sub_total = potential_subs['ExpenseAmount'].sum()
        sub_count = len(potential_subs)
        insights.append({
            'icon': '',
            'title': 'Recurring Subscriptions',
            'text': f"{sub_count} subscription charges totaling <strong>${sub_total:,.0f}</strong>"
        })

    # Weekend vs weekday spending
    expenses_copy = expenses.copy()
    expenses_copy['IsWeekend'] = expenses_copy['DayOfWeek'].isin(['Saturday', 'Sunday'])
    weekend_spend = expenses_copy[expenses_copy['IsWeekend']]['ExpenseAmount'].sum()
    weekday_spend = expenses_copy[~expenses_copy['IsWeekend']]['ExpenseAmount'].sum()
    if weekend_spend > weekday_spend * 0.5:
        insights.append({
            'icon': '',
            'title': 'Weekend Spending',
            'text': f"Weekend spending is <strong>${weekend_spend:,.0f}</strong> ({weekend_spend/(weekend_spend+weekday_spend)*100:.0f}% of total)"
        })

    # Top merchant
    if 'Merchant' in expenses.columns:
        merchants = expenses[expenses['Merchant'].notna() & (expenses['Merchant'] != '')]
        if not merchants.empty:
            top_merchant = merchants.groupby('Merchant')['ExpenseAmount'].sum().idxmax()
            top_merchant_amt = merchants.groupby('Merchant')['ExpenseAmount'].sum().max()
            insights.append({
                'icon': '',
                'title': 'Top Merchant',
                'text': f"<strong>{top_merchant}</strong>: ${top_merchant_amt:,.0f} total"
            })

    return insights[:4]


def render_stats_bar(total_expenses: float, total_income: float, net: float, tx_count: int):
    """Render the quick stats bar at the top."""
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0

    st.markdown(f"""
    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-label">Total Income</div>
            <div class="stat-value">${total_income:,.0f}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Total Expenses</div>
            <div class="stat-value">${total_expenses:,.0f}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Net Balance</div>
            <div class="stat-value">${net:,.0f}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Savings Rate</div>
            <div class="stat-value">{savings_rate:.1f}%</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Transactions</div>
            <div class="stat-value">{tx_count:,}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(title: str, value: str, trend: str = None, trend_direction: str = None):
    """Render a styled metric card."""
    value_class = ""
    if "+" in value or (trend_direction == "up" and "Expenses" not in title):
        value_class = "positive"
    elif "-" in value or trend_direction == "down":
        value_class = "negative"

    trend_html = ""
    if trend:
        trend_class = "up" if trend_direction == "up" else "down" if trend_direction == "down" else ""
        trend_html = f'<div class="trend {trend_class}">{trend}</div>'

    st.markdown(f"""
    <div class="metric-card">
        <h3>{title}</h3>
        <p class="value {value_class}">{value}</p>
        {trend_html}
    </div>
    """, unsafe_allow_html=True)


def render_alerts(staleness_alerts: list, anomalies: list, df: pd.DataFrame):
    """Render alert banners with AI explanations."""
    if not staleness_alerts and not anomalies:
        return

    st.markdown('<div class="section-header"><h2>Alerts</h2></div>', unsafe_allow_html=True)

    # Staleness alerts (unchanged)
    for alert in staleness_alerts:
        st.markdown(f"""
        <div class="alert-box alert-warning">
            <span class="alert-icon"></span>
            <div class="alert-content">
                <div class="alert-title">Statement Overdue</div>
                <div class="alert-text"><strong>{alert['account']}</strong> has no statement for {alert['days_old']} days (last: {alert['last_date']})</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Anomaly alerts with AI explanation
    for anomaly in anomalies[:3]:
        # Get explanation (with session caching)
        cache_key = f"anomaly_{anomaly['name']}_{anomaly['current']}"
        if cache_key not in st.session_state:
            cat_transactions = df[df['Category'] == anomaly['name']].to_dict('records')
            st.session_state[cache_key] = explain_anomaly(
                anomaly['name'],
                anomaly['current'],
                anomaly['average'],
                cat_transactions
            )

        explanation = st.session_state[cache_key]

        st.markdown(f"""
        <div class="alert-box alert-info">
            <span class="alert-icon"></span>
            <div class="alert-content">
                <div class="alert-title">Spending Spike: {anomaly['name']}</div>
                <div class="alert-text">{explanation}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def create_donut_chart(df: pd.DataFrame, title: str):
    """Create a styled donut chart with center total."""
    expense_by_cat = df.groupby('Category')['ExpenseAmount'].sum().reset_index()
    expense_by_cat = expense_by_cat[expense_by_cat['ExpenseAmount'] > 0]
    expense_by_cat = expense_by_cat.sort_values('ExpenseAmount', ascending=False)

    total = expense_by_cat['ExpenseAmount'].sum()

    colors = [get_category_color(cat) for cat in expense_by_cat['Category']]

    fig = go.Figure(data=[go.Pie(
        labels=expense_by_cat['Category'],
        values=expense_by_cat['ExpenseAmount'],
        hole=0.6,
        marker_colors=colors,
        textinfo='percent',
        textposition='outside',
        textfont_size=12,
        hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>"
    )])

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#1e293b')),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11)
        ),
        annotations=[dict(
            text=f'<b>${total:,.0f}</b><br><span style="font-size:12px;color:#64748b">Total</span>',
            x=0.5, y=0.5,
            font_size=20,
            showarrow=False,
            font_color='#1e293b'
        )],
        height=400,
        margin=dict(l=20, r=120, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_monthly_trend_chart(df: pd.DataFrame):
    """Create monthly income vs expenses chart."""
    monthly = df.groupby('MonthStr').agg({
        'ExpenseAmount': 'sum',
        'IncomeAmount': 'sum'
    }).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly['MonthStr'],
        y=monthly['IncomeAmount'],
        name='Income',
        marker_color='#04d38c',
        marker_line_width=0,
        hovertemplate='Income: $%{y:,.0f}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=monthly['MonthStr'],
        y=monthly['ExpenseAmount'],
        name='Expenses',
        marker_color='#ef4444',
        marker_line_width=0,
        hovertemplate='Expenses: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text='Monthly Income vs Expenses', font=dict(size=16, color='#1e293b')),
        barmode='group',
        height=400,
        xaxis=dict(title='', tickfont=dict(size=11)),
        yaxis=dict(title='', tickformat='$,.0f', tickfont=dict(size=11)),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        bargap=0.3
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e2e8f0')

    return fig


def create_top_merchants_chart(df: pd.DataFrame):
    """Create top merchants horizontal bar chart."""
    merchants = df[df['Merchant'].notna() & (df['Merchant'] != '')]
    top_merchants = merchants.groupby('Merchant')['ExpenseAmount'].sum().nlargest(8).reset_index()
    top_merchants = top_merchants.sort_values('ExpenseAmount', ascending=True)

    fig = go.Figure(go.Bar(
        x=top_merchants['ExpenseAmount'],
        y=top_merchants['Merchant'],
        orientation='h',
        marker=dict(
            color='#1a73e8',
            line=dict(width=0)
        ),
        hovertemplate='<b>%{y}</b><br>$%{x:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text='Top Merchants', font=dict(size=16, color='#1e293b')),
        height=400,
        xaxis=dict(title='', tickformat='$,.0f', tickfont=dict(size=11)),
        yaxis=dict(title='', tickfont=dict(size=11)),
        margin=dict(l=20, r=20, t=60, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e2e8f0')
    fig.update_yaxes(showgrid=False)

    return fig


def create_category_trend_chart(df: pd.DataFrame):
    """Create category trend line chart."""
    cat_monthly = df.groupby(['MonthStr', 'Category'])['ExpenseAmount'].sum().reset_index()
    top_cats = df.groupby('Category')['ExpenseAmount'].sum().nlargest(5).index
    cat_monthly = cat_monthly[cat_monthly['Category'].isin(top_cats)]

    fig = go.Figure()

    for category in top_cats:
        cat_data = cat_monthly[cat_monthly['Category'] == category]
        fig.add_trace(go.Scatter(
            x=cat_data['MonthStr'],
            y=cat_data['ExpenseAmount'],
            mode='lines+markers',
            name=category,
            line=dict(color=get_category_color(category), width=2),
            marker=dict(size=8),
            hovertemplate='<b>%{fullData.name}</b><br>$%{y:,.0f}<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text='Category Trends (Top 5)', font=dict(size=16, color='#1e293b')),
        height=400,
        xaxis=dict(title='', tickfont=dict(size=11)),
        yaxis=dict(title='', tickformat='$,.0f', tickfont=dict(size=11)),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=10)),
        margin=dict(l=20, r=20, t=80, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e2e8f0')

    return fig


def render_insights(insights: list):
    """Render insight cards."""
    if not insights:
        st.info("Add more transactions to see spending insights!")
        return

    cols = st.columns(len(insights))
    for i, insight in enumerate(insights):
        with cols[i]:
            st.markdown(f"""
            <div class="insight-card">
                <div class="insight-icon">{insight['icon']}</div>
                <div class="insight-title">{insight['title']}</div>
                <div class="insight-text">{insight['text']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_category_management(categories: list):
    """Render category management section in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("Category Management")

    # Add new category
    new_cat = st.sidebar.text_input("New Category Name", key="new_category_input")
    if st.sidebar.button("Add Category", key="add_category_btn"):
        if new_cat and new_cat.strip():
            if add_category(new_cat.strip()):
                st.sidebar.success(f"Added: {new_cat}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.sidebar.error("Failed to add category")
        else:
            st.sidebar.warning("Enter a category name")

    # Show existing categories
    with st.sidebar.expander("View Categories"):
        for cat in sorted(categories):
            color = get_category_color(cat)
            st.markdown(f'<span style="color:{color};">{cat}</span>', unsafe_allow_html=True)


def render_transaction_editor(df: pd.DataFrame, categories: list):
    """Render transaction table with editing capabilities."""
    st.markdown('<div class="section-header"><h2>Transactions</h2></div>', unsafe_allow_html=True)

    # Tabs for different views
    tab1, tab2 = st.tabs(["Recent Transactions", "Bulk Re-categorize"])

    with tab1:
        # Recent transactions with inline editing
        recent = df.nlargest(50, 'Date').copy()
        recent['DateStr'] = recent['Date'].dt.strftime('%Y-%m-%d')

        display_df = recent[['ID', 'DateStr', 'Description', 'Amount', 'Category', 'Merchant', 'Account']].copy()
        display_df.columns = ['ID', 'Date', 'Description', 'Amount', 'Category', 'Merchant', 'Account']

        # Add currency columns if available
        if 'Original Currency' in recent.columns:
            display_df['Original Currency'] = recent['Original Currency']
        if 'Original Amount' in recent.columns:
            display_df['Original Amount'] = recent['Original Amount']
        if 'HKD Amount' in recent.columns:
            display_df['HKD Amount'] = recent['HKD Amount']

        column_config = {
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Date": st.column_config.TextColumn("Date", disabled=True),
            "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
            "Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=categories,
                required=True,
                width="medium"
            ),
            "Merchant": st.column_config.TextColumn("Merchant", disabled=True),
            "Account": st.column_config.TextColumn("Account", disabled=True)
        }

        # Add currency column configs if present
        if 'Original Currency' in display_df.columns:
            column_config["Original Currency"] = st.column_config.TextColumn("Orig. Currency", width="small", disabled=True)
        if 'Original Amount' in display_df.columns:
            column_config["Original Amount"] = st.column_config.NumberColumn("Orig. Amount", format="%.2f", disabled=True)
        if 'HKD Amount' in display_df.columns:
            column_config["HKD Amount"] = st.column_config.NumberColumn("HKD Amount", format="$%.2f", disabled=True)

        edited_df = st.data_editor(
            display_df,
            column_config=column_config,
            hide_index=True,
            width="stretch",
            key="transaction_editor"
        )

        # Check for changes and save
        if edited_df is not None and not edited_df.empty:
            changes = []
            # Reset indices to ensure proper comparison
            original_df = display_df.reset_index(drop=True)
            edited_reset = edited_df.reset_index(drop=True)

            for i in range(len(edited_reset)):
                if i < len(original_df):
                    original_cat = original_df.loc[i, 'Category']
                    new_cat = edited_reset.loc[i, 'Category']
                    if original_cat != new_cat:
                        changes.append((edited_reset.loc[i, 'ID'], new_cat))

            if changes:
                if st.button("Save Category Changes", type="primary"):
                    success_count = 0
                    for tx_id, new_category in changes:
                        if update_transaction_category(tx_id, new_category):
                            success_count += 1

                            # Capture for learning
                            # Find the transaction row to get merchant and description
                            tx_row = original_df[original_df['ID'] == tx_id].iloc[0]
                            original_cat = tx_row['Category']
                            merchant = recent[recent['ID'] == tx_id]['Merchant'].iloc[0] if 'Merchant' in recent.columns else ''
                            description = tx_row['Description']

                            capture_correction(
                                merchant=merchant,
                                description=description,
                                old_category=original_cat,
                                new_category=new_category
                            )

                    if success_count == len(changes):
                        st.success(f"Updated {success_count} transaction(s)")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning(f"Updated {success_count} of {len(changes)} transactions")

    with tab2:
        # Bulk re-categorization
        st.write("Select transactions to re-categorize in bulk:")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            filter_cat = st.selectbox("Filter by current category", ["All"] + categories, key="bulk_filter_cat")
        with col2:
            filter_merchant = st.text_input("Filter by merchant (contains)", key="bulk_filter_merchant")

        # Filter transactions
        bulk_df = df.copy()
        if filter_cat != "All":
            bulk_df = bulk_df[bulk_df['Category'] == filter_cat]
        if filter_merchant:
            bulk_df = bulk_df[bulk_df['Merchant'].str.contains(filter_merchant, case=False, na=False)]

        bulk_df = bulk_df.nlargest(100, 'Date')

        if not bulk_df.empty:
            # Add selection column
            bulk_df['Select'] = False
            bulk_df['DateStr'] = bulk_df['Date'].dt.strftime('%Y-%m-%d')

            select_df = bulk_df[['Select', 'ID', 'DateStr', 'Description', 'Amount', 'Category', 'Merchant']].copy()
            select_df.columns = ['Select', 'ID', 'Date', 'Description', 'Amount', 'Category', 'Merchant']

            edited_bulk = st.data_editor(
                select_df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", default=False),
                    "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
                    "Date": st.column_config.TextColumn("Date", disabled=True),
                    "Description": st.column_config.TextColumn("Description", disabled=True, width="large"),
                    "Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
                    "Category": st.column_config.TextColumn("Category", disabled=True),
                    "Merchant": st.column_config.TextColumn("Merchant", disabled=True)
                },
                hide_index=True,
                width="stretch",
                key="bulk_editor"
            )

            # Apply new category to selected
            selected_ids = edited_bulk[edited_bulk['Select'] == True]['ID'].tolist()

            if selected_ids:
                st.write(f"**{len(selected_ids)} transaction(s) selected**")
                new_category = st.selectbox("Apply new category", categories, key="bulk_new_category")

                if st.button("Apply to Selected", type="primary"):
                    if update_transaction_categories_bulk(selected_ids, new_category):
                        # Capture for learning - batch version to avoid rate limits
                        corrections = []
                        for tx_id in selected_ids:
                            tx_row = bulk_df[bulk_df['ID'] == tx_id].iloc[0]
                            corrections.append({
                                'merchant': tx_row['Merchant'] if 'Merchant' in bulk_df.columns else '',
                                'description': tx_row['Description'],
                                'old_category': tx_row['Category'],
                                'new_category': new_category
                            })

                        capture_corrections_bulk(corrections)

                        st.success(f"Updated {len(selected_ids)} transactions to '{new_category}'")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to update transactions")
        else:
            st.info("No transactions match the filter criteria")


def render_insights_tab():
    """Render the Insights tab with weekly digests and forecasts."""
    st.markdown('<div class="section-header"><h2>AI Insights</h2></div>', unsafe_allow_html=True)

    insights = get_latest_insights(limit=4)

    if not insights:
        st.info("No insights generated yet. Weekly digests are generated every Sunday at 9am.")
        return

    # Show latest digest
    latest = insights[0]
    st.markdown(f"""
    <div style="background: #1a1a2e; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
        <div style="color: #04d38c; font-weight: bold; margin-bottom: 10px;">Week of {latest.get('Week Start', '')} to {latest.get('Week End', '')}</div>
        <div>{latest.get('Digest', 'No summary available')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Show highlights
    try:
        highlights = json.loads(latest.get('Top Insights', '[]'))
        if highlights:
            st.subheader("Highlights")
            for h in highlights:
                st.markdown(f"- {h}")
    except json.JSONDecodeError:
        pass

    # Show forecast
    with st.expander("3-Month Forecast", expanded=True):
        forecast = generate_forecast(months_ahead=3)

        if forecast.get("need_more_data"):
            st.warning(forecast.get("message", "Need more data"))
        elif "error" in forecast:
            st.error(forecast["error"])
        else:
            forecast_data = []
            for fm in forecast.get("forecast_months", []):
                forecast_data.append({
                    "Month": fm["month"],
                    "Projected": fm["projected_total"],
                    "Confidence": fm["confidence"]
                })

            if forecast_data:
                df_forecast = pd.DataFrame(forecast_data)
                fig = px.bar(
                    df_forecast, x="Month", y="Projected",
                    title="Spending Forecast",
                    color="Confidence",
                    color_discrete_map={"high": "#04d38c", "medium": "#f59e0b", "low": "#ef4444"}
                )
                st.plotly_chart(fig, use_container_width=True)

            trends = forecast.get("trends", {})
            if trends.get("overall"):
                st.markdown(f"**Trend:** {trends['overall']}")


def render_cash_tab():
    """Render Cash tab with withdrawals and spend entry."""
    st.markdown('<div class="section-header"><h2>💵 Cash Tracking</h2></div>', unsafe_allow_html=True)

    from sheets_sync import get_cash_withdrawals_with_balance, get_cash_spends_for_withdrawal, add_cash_spend, get_categories

    withdrawals = get_cash_withdrawals_with_balance()

    if not withdrawals:
        st.info("No cash withdrawals found. ATM withdrawals from statements will appear here automatically.")
        return

    # Summary metrics
    total_withdrawn = sum(w.get("Withdrawal Amount", 0) for w in withdrawals)
    total_remaining = sum(w.get("Actual Remaining", 0) for w in withdrawals)
    total_spent = total_withdrawn - total_remaining

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Withdrawn", f"${total_withdrawn:,.0f}")
    with col2:
        st.metric("Cash Spent", f"${total_spent:,.0f}")
    with col3:
        st.metric("Cash Remaining", f"${total_remaining:,.0f}")

    st.markdown("---")

    # Two columns: withdrawals list + add spend form
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### ATM Withdrawals")
        for w in sorted(withdrawals, key=lambda x: x.get("Date", ""), reverse=True):
            remaining = w.get("Actual Remaining", 0)
            amount = w.get("Withdrawal Amount", 0)
            allocated_pct = ((amount - remaining) / amount * 100) if amount > 0 else 0

            color = "#04d38c" if remaining <= 0 else "#1a73e8"

            st.markdown(f"""
            <div style="border-left: 4px solid {color}; background: white; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 600; color: #1e293b;">{w.get('Date')}</div>
                        <div style="font-size: 0.875rem; color: #64748b;">{w.get('Source Account')}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.25rem; font-weight: 700; color: #1e293b;">${amount:,.0f}</div>
                        <div style="font-size: 0.875rem; color: {'#04d38c' if remaining <= 0 else '#ef4444'};">${remaining:,.0f} left</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"View spends from this withdrawal"):
                spends = get_cash_spends_for_withdrawal(w["Cash TX ID"])
                if spends:
                    df_spends = pd.DataFrame(spends)[['Date', 'Description', 'Amount', 'Category']]
                    st.dataframe(df_spends, hide_index=True, use_container_width=True)
                else:
                    st.info("No spends recorded yet")

    with col_right:
        st.markdown("### Add Cash Spend")

        available_withdrawals = {
            f"{w['Date']} - ${w.get('Withdrawal Amount', 0):,.0f} (${w.get('Actual Remaining', 0):,.0f} left)": w['Cash TX ID']
            for w in withdrawals if w.get('Actual Remaining', 0) > 0
        }

        if not available_withdrawals:
            st.warning("All withdrawals fully allocated. Make a new ATM withdrawal to add cash spends.")
        else:
            selected_display = st.selectbox("From Withdrawal", list(available_withdrawals.keys()))
            selected_id = available_withdrawals[selected_display]

            selected_w = next(w for w in withdrawals if w['Cash TX ID'] == selected_id)
            max_amt = selected_w.get('Actual Remaining', 0)

            st.info(f"Available cash: ${max_amt:,.2f}")

            with st.form("add_cash_form"):
                spend_date = st.date_input("Date", value=datetime.now().date())
                spend_desc = st.text_input("Description", placeholder="Coffee, taxi, groceries, etc.")
                spend_amt = st.number_input("Amount", min_value=0.01, max_value=float(max_amt), step=0.01)

                cats = get_categories()
                cash_cats = [c for c in cats if c not in ["Cash Withdrawal", "Transfer", "Income", "Credit Card Payment"]]
                spend_cat = st.selectbox("Category", cash_cats)

                if st.form_submit_button("Add Cash Spend", type="primary"):
                    if not spend_desc:
                        st.error("Please enter a description")
                    else:
                        result = add_cash_spend(selected_id, spend_date.strftime("%Y-%m-%d"), spend_desc, spend_amt, spend_cat)
                        if result["success"]:
                            st.success(result["message"])
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(result["message"])


def main():
    # Header
    st.markdown("""
    <h1 style="color: #1e293b; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">
        Finance Tracker
    </h1>
    """, unsafe_allow_html=True)

    # Load data
    df, accounts_df = load_data()
    categories = load_categories()

    if df.empty:
        st.markdown("""
        <div class="alert-box alert-info">
            <span class="alert-icon"></span>
            <div class="alert-content">
                <div class="alert-title">No Data Found</div>
                <div class="alert-text">Drop some PDF statements in your folder to get started! Dashboard will refresh automatically when data is available.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Prepare data
    df = prepare_data(df)

    # Sidebar filters
    st.sidebar.header("Filters")

    # Date range filter
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Category filter
    category_options = ['All'] + sorted(df['Category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category", category_options)

    # Account filter
    accounts = ['All'] + sorted(df['Account'].unique().tolist())
    selected_account = st.sidebar.selectbox("Account", accounts)

    # Currency filter
    if 'Original Currency' in df.columns:
        currencies = ['All'] + sorted(df['Original Currency'].dropna().unique().tolist())
        selected_currency = st.sidebar.selectbox("Currency", currencies)
    else:
        selected_currency = 'All'

    # Exclude CC payments from analysis
    exclude_cc_payments = st.sidebar.checkbox("Exclude CC Payments", value=True,
                                              help="Exclude credit card payments to avoid double-counting")
    exclude_cash_withdrawals = st.sidebar.checkbox("Exclude Cash Withdrawals", value=False,
                                                   help="Exclude ATM withdrawals (tracked separately in Cash tab)")

    # Category management
    render_category_management(categories)

    # Apply filters
    mask = (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
    if selected_category != 'All':
        mask &= df['Category'] == selected_category
    if selected_account != 'All':
        mask &= df['Account'] == selected_account
    if selected_currency != 'All' and 'Original Currency' in df.columns:
        mask &= df['Original Currency'] == selected_currency
    if exclude_cc_payments and 'Is CC Payment' in df.columns:
        mask &= ~df['Is CC Payment']
    if exclude_cash_withdrawals:
        mask &= df['Category'] != 'Cash Withdrawal'

    filtered_df = df[mask]

    # Check for alerts
    staleness_alerts = check_staleness(accounts_df)
    anomalies = detect_anomalies(df)

    # Render alerts
    render_alerts(staleness_alerts, anomalies, filtered_df)

    # Key metrics
    total_expenses = filtered_df['ExpenseAmount'].sum()
    total_income = filtered_df['IncomeAmount'].sum()
    net = total_income - total_expenses
    tx_count = len(filtered_df)

    # Quick stats bar
    render_stats_bar(total_expenses, total_income, net, tx_count)

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Transactions", "Insights", "Cash"])

    with tab1:
        # Charts section
        st.markdown('<div class="section-header"><h2>Spending Analysis</h2></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = create_donut_chart(filtered_df, "Spending by Category")
            st.plotly_chart(fig, width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = create_monthly_trend_chart(filtered_df)
            st.plotly_chart(fig, width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = create_top_merchants_chart(filtered_df)
            st.plotly_chart(fig, width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            fig = create_category_trend_chart(filtered_df)
            st.plotly_chart(fig, width="stretch")
            st.markdown('</div>', unsafe_allow_html=True)

        # Insights section
        st.markdown('<div class="section-header"><h2>Insights</h2></div>', unsafe_allow_html=True)
        insights = generate_insights(filtered_df)
        render_insights(insights)

    with tab2:
        # Transaction editor
        render_transaction_editor(filtered_df, categories)

    with tab3:
        # AI Insights tab
        render_insights_tab()

    with tab4:
        # Cash Tracking tab
        render_cash_tab()

    # Footer
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data from Google Sheets")
    with col2:
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
