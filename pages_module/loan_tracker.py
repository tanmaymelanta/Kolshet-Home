import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from aws_helpers import get_dynamodb_resource, LOAN_CONFIG_TABLE


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def load_loan_config():
    try:
        db = get_dynamodb_resource()
        table = db.Table(LOAN_CONFIG_TABLE)
        response = table.get_item(Key={'config_id': 'home_loan'})
        item = response.get('Item')
        if item:
            return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}
    except Exception as e:
        st.warning(f"Could not load loan config: {e}")
    return None


def save_loan_config(config: dict):
    try:
        db = get_dynamodb_resource()
        table = db.Table(LOAN_CONFIG_TABLE)
        item = {k: Decimal(str(v)) if isinstance(v, float) else v for k, v in config.items()}
        item['config_id'] = 'home_loan'
        table.put_item(Item=item)
        return True
    except Exception as e:
        st.error(f"Could not save loan config: {e}")
        return False


# ── Amortization logic ────────────────────────────────────────────────────────

def compute_emi(principal, annual_rate, tenure_months):
    r = annual_rate / 12 / 100
    if r == 0:
        return principal / tenure_months
    return principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)


def build_amortization(principal, annual_rate, tenure_months, start_date):
    emi = compute_emi(principal, annual_rate, tenure_months)
    r = annual_rate / 12 / 100
    rows = []
    balance = principal
    for i in range(1, tenure_months + 1):
        interest = balance * r
        principal_part = emi - interest
        balance -= principal_part
        balance = max(balance, 0)
        rows.append({
            'month': i,
            'date': start_date + relativedelta(months=i - 1),
            'emi': round(emi, 2),
            'principal': round(principal_part, 2),
            'interest': round(interest, 2),
            'balance': round(balance, 2)
        })
    return pd.DataFrame(rows), emi


# ── Render ────────────────────────────────────────────────────────────────────

def render():
    st.title("📊 Loan Tracker")

    config = load_loan_config()

    # ── Config form ───────────────────────────────────────────────────────────
    with st.expander("⚙️ Loan Configuration", expanded=config is None):
        st.caption("Fill this in once your bank confirms the loan details.")
        with st.form("loan_config_form"):
            col1, col2 = st.columns(2)
            with col1:
                sanctioned = st.number_input(
                    "Sanctioned Amount (₹)",
                    min_value=0.0, step=100000.0,
                    value=float(config['sanctioned_amount']) if config else 0.0
                )
                annual_rate = st.number_input(
                    "Interest Rate (% per annum)",
                    min_value=0.0, max_value=30.0, step=0.05,
                    value=float(config['annual_rate']) if config else 8.5
                )
                tenure_years = st.number_input(
                    "Tenure (years)",
                    min_value=1, max_value=30, step=1,
                    value=int(config['tenure_years']) if config else 30
                )
            with col2:
                emi_start = st.date_input(
                    "EMI Start Date",
                    value=datetime.strptime(config['emi_start'], '%Y-%m-%d').date() if config else date.today()
                )
                principal_paid = st.number_input(
                    "Principal Paid Till Now (₹)",
                    min_value=0.0, step=1000.0,
                    value=float(config['principal_paid']) if config else 0.0
                )
                interest_paid = st.number_input(
                    "Interest Paid Till Now (₹)",
                    min_value=0.0, step=1000.0,
                    value=float(config['interest_paid']) if config else 0.0
                )

            if st.form_submit_button("💾 Save Loan Config"):
                ok = save_loan_config({
                    'sanctioned_amount': sanctioned,
                    'annual_rate': annual_rate,
                    'tenure_years': tenure_years,
                    'emi_start': emi_start.strftime('%Y-%m-%d'),
                    'principal_paid': principal_paid,
                    'interest_paid': interest_paid
                })
                if ok:
                    st.success("Saved! Refresh to see updated dashboard.")
                    st.rerun()

    if not config:
        st.info("Configure your loan details above to see the dashboard.")
        return

    # ── Computed values ───────────────────────────────────────────────────────
    sanctioned = config['sanctioned_amount']
    annual_rate = config['annual_rate']
    tenure_years = config['tenure_years']
    tenure_months = int(tenure_years * 12)
    emi_start = datetime.strptime(config['emi_start'], '%Y-%m-%d').date()
    principal_paid = config['principal_paid']
    interest_paid = config['interest_paid']
    total_paid = principal_paid + interest_paid
    principal_remaining = sanctioned - principal_paid
    today = date.today()

    df, emi = build_amortization(sanctioned, annual_rate, tenure_months, emi_start)
    total_interest = df['interest'].sum()
    total_payable = sanctioned + total_interest

    # EMIs completed
    emis_done = max(0, (today.year - emi_start.year) * 12 + (today.month - emi_start.month))
    emis_remaining = max(0, tenure_months - emis_done)

    # Projected end date
    projected_end = emi_start + relativedelta(months=tenure_months)

    # ── KPI cards ─────────────────────────────────────────────────────────────
    st.markdown("### Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Loan Amount", f"₹{sanctioned:,.0f}")
    c2.metric("Monthly EMI", f"₹{emi:,.0f}")
    c3.metric("EMIs Done", f"{emis_done} / {tenure_months}")
    c4.metric("Loan Closes", projected_end.strftime("%b %Y"))

    st.markdown("---")
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Principal Paid", f"₹{principal_paid:,.0f}", f"{principal_paid/sanctioned*100:.1f}%")
    c6.metric("Interest Paid", f"₹{interest_paid:,.0f}")
    c7.metric("Principal Remaining", f"₹{principal_remaining:,.0f}")
    c8.metric("Total Interest (lifetime)", f"₹{total_interest:,.0f}")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Loan Repayment Progress")
        fig_donut = go.Figure(go.Pie(
            values=[principal_paid, principal_remaining],
            labels=["Paid", "Remaining"],
            hole=0.65,
            marker_colors=["#2ecc71", "#e74c3c"],
            textinfo='label+percent'
        ))
        fig_donut.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            annotations=[dict(
                text=f"₹{principal_paid/sanctioned*100:.1f}%<br>done",
                x=0.5, y=0.5,
                font_size=16,
                showarrow=False
            )]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        st.markdown("#### Total Outflow Breakdown")
        fig_bar = go.Figure(go.Bar(
            x=["Principal", "Total Interest"],
            y=[sanctioned, total_interest],
            marker_color=["#3498db", "#e67e22"],
            text=[f"₹{sanctioned:,.0f}", f"₹{total_interest:,.0f}"],
            textposition='outside'
        ))
        fig_bar.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            yaxis_title="Amount (₹)",
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Amortization chart ────────────────────────────────────────────────────
    st.markdown("#### EMI Breakdown Over Time (Principal vs Interest)")
    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=df['date'], y=df['principal'],
        name='Principal', fill='tozeroy',
        line=dict(color='#2ecc71')
    ))
    fig_area.add_trace(go.Scatter(
        x=df['date'], y=df['interest'],
        name='Interest', fill='tozeroy',
        line=dict(color='#e74c3c')
    ))
    fig_area.add_vline(
        x=str(today), line_dash="dash",
        line_color="white", annotation_text="Today"
    )
    fig_area.update_layout(
        height=350,
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis_title="Date",
        yaxis_title="Amount (₹)",
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # ── Outstanding balance curve ─────────────────────────────────────────────
    st.markdown("#### Outstanding Balance Over Time")
    fig_balance = px.line(df, x='date', y='balance', color_discrete_sequence=["#3498db"])
    fig_balance.add_vline(
        x=str(today), line_dash="dash",
        line_color="orange", annotation_text="Today"
    )
    fig_balance.update_layout(
        height=300,
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis_title="Date",
        yaxis_title="Outstanding (₹)"
    )
    st.plotly_chart(fig_balance, use_container_width=True)

    # ── Amortization table ────────────────────────────────────────────────────
    with st.expander("📋 Full Amortization Schedule"):
        display_df = df.copy()
        display_df['date'] = display_df['date'].apply(lambda d: d.strftime('%b %Y'))
        display_df.columns = ['Month', 'Date', 'EMI (₹)', 'Principal (₹)', 'Interest (₹)', 'Balance (₹)']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
