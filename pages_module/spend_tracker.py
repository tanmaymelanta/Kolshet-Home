import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import uuid
from datetime import date, datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from aws_helpers import (
    get_dynamodb_resource, get_s3_client,
    TRANSACTIONS_TABLE, SPEND_CATEGORIES, BUCKET_NAME
)

API_URL = st.secrets.get("API_GATEWAY_URL", "")  # e.g. https://xyz.execute-api.ap-south-1.amazonaws.com/dev


# ── DynamoDB helpers ──────────────────────────────────────────────────────────

def load_transactions():
    try:
        db = get_dynamodb_resource()
        table = db.Table(TRANSACTIONS_TABLE)
        response = table.scan()
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        records = []
        for item in items:
            records.append({
                'transaction_id': item.get('transaction_id', ''),
                'document_id': item.get('document_id', ''),
                'txn_date': item.get('txn_date', ''),
                'category': item.get('category', 'Other'),
                'comments': item.get('comments', ''),
                'expected_amount': float(item.get('expected_amount', 0)),
                'ocr_amount': float(item.get('ocr_amount', 0)),
                'status': item.get('status', ''),
                's3_path': item.get('s3_path', ''),
            })
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Could not load transactions: {e}")
        return pd.DataFrame()


# ── Upload helpers ────────────────────────────────────────────────────────────

def call_metadata_api(txn_id, txn_date, amount, category, doc_index, file_ext, content_type, comments):
    payload = {
        "transaction_id": txn_id,
        "txn_date": txn_date,
        "amount": str(amount),
        "category": category,
        "document_id": str(doc_index),
        "file_extension": file_ext,
        "content_type": content_type,
        "comments": comments
    }
    response = requests.post(f"{API_URL}/upload-metadata", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def upload_to_presigned_url(upload_url, file_bytes, content_type):
    response = requests.put(
        upload_url,
        data=file_bytes,
        headers={"Content-Type": content_type},
        timeout=30
    )
    response.raise_for_status()


def get_content_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    mapping = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png'
    }
    return mapping.get(ext, 'application/octet-stream')


# ── Render ────────────────────────────────────────────────────────────────────

def render():
    st.title("💸 Spend Tracker")

    tab_dashboard, tab_add = st.tabs(["📊 Dashboard", "➕ Add Transaction"])

    # ── Dashboard tab ─────────────────────────────────────────────────────────
    with tab_dashboard:
        df = load_transactions()

        if df.empty:
            st.info("No transactions yet. Add your first one in the 'Add Transaction' tab.")
            return

        # Filter to validated only for spend analysis
        validated = df[df['status'] == 'VALIDATED'].copy()

        if validated.empty:
            st.info("No validated transactions yet.")
        else:
            total_spend = validated['expected_amount'].sum()
            num_txns = len(validated['transaction_id'].unique())
            top_category = validated.groupby('category')['expected_amount'].sum().idxmax()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Spend", f"₹{total_spend:,.0f}")
            c2.metric("Transactions", num_txns)
            c3.metric("Top Category", top_category)

            st.markdown("---")

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### Spend by Category")
                cat_df = validated.groupby('category')['expected_amount'].sum().reset_index()
                fig_pie = px.pie(
                    cat_df, values='expected_amount', names='category',
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.4
                )
                fig_pie.update_layout(margin=dict(t=10, b=10), height=320)
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_right:
                st.markdown("#### Monthly Spend")
                validated['month'] = validated['txn_date'].apply(
                    lambda d: datetime.strptime(str(d), '%Y%m%d').strftime('%Y-%m') if len(str(d)) == 8 else d[:7]
                )
                monthly = validated.groupby('month')['expected_amount'].sum().reset_index()
                monthly = monthly.sort_values('month')
                fig_bar = px.bar(
                    monthly, x='month', y='expected_amount',
                    color_discrete_sequence=["#3498db"],
                    labels={'expected_amount': 'Amount (₹)', 'month': 'Month'}
                )
                fig_bar.update_layout(margin=dict(t=10, b=10), height=320)
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### Category-wise Spend Over Time")
            validated['month'] = validated['txn_date'].apply(
                lambda d: datetime.strptime(str(d), '%Y%m%d').strftime('%Y-%m') if len(str(d)) == 8 else d[:7]
            )
            pivot = validated.groupby(['month', 'category'])['expected_amount'].sum().reset_index()
            fig_stack = px.bar(
                pivot, x='month', y='expected_amount', color='category',
                color_discrete_sequence=px.colors.qualitative.Set2,
                labels={'expected_amount': 'Amount (₹)', 'month': 'Month'}
            )
            fig_stack.update_layout(margin=dict(t=10, b=10), height=350)
            st.plotly_chart(fig_stack, use_container_width=True)

        # ── Full transaction table ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### All Transactions")

        status_filter = st.multiselect(
            "Filter by status",
            options=df['status'].unique().tolist(),
            default=df['status'].unique().tolist()
        )

        filtered = df[df['status'].isin(status_filter)]

        status_colors = {
            'VALIDATED': '🟢',
            'AMOUNT_MISMATCH': '🟡',
            'OCR_FAILED': '🔴',
            'PENDING': '⚪'
        }

        display = filtered[[
            'transaction_id', 'txn_date', 'category',
            'expected_amount', 'ocr_amount', 'status', 'comments'
        ]].copy()
        display['status'] = display['status'].apply(lambda s: f"{status_colors.get(s, '')} {s}")
        display['txn_date'] = display['txn_date'].apply(
            lambda d: datetime.strptime(str(d), '%Y%m%d').strftime('%d %b %Y') if len(str(d)) == 8 else d
        )
        display.columns = ['Txn ID', 'Date', 'Category', 'Expected (₹)', 'OCR Amount (₹)', 'Status', 'Comments']
        st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Add transaction tab ───────────────────────────────────────────────────
    with tab_add:
        st.markdown("### New Transaction")

        with st.form("add_txn_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                txn_id = st.text_input("Transaction ID *", placeholder="e.g. T2605161611411488265779")
                txn_date = st.date_input("Transaction Date *", value=date.today())
                amount = st.number_input("Amount (₹) *", min_value=0.0, step=100.0)
            with col2:
                category = st.selectbox("Category *", SPEND_CATEGORIES)
                comments = st.text_area("Comments (optional)", placeholder="e.g. Home token payment to Square Feet Group")

            st.markdown("#### Supporting Documents")
            st.caption("Upload one or more receipts / statements / bills.")
            uploaded_files = st.file_uploader(
                "Choose files",
                accept_multiple_files=True,
                type=['pdf', 'jpg', 'jpeg', 'png']
            )

            submitted = st.form_submit_button("🚀 Submit Transaction", use_container_width=True)

        if submitted:
            if not API_URL:
                st.error("API_GATEWAY_URL not set in Streamlit secrets.")
            elif not txn_id or amount <= 0:
                st.error("Transaction ID and Amount are required.")
            elif not uploaded_files:
                st.error("Please upload at least one supporting document.")
            else:
                txn_date_str = txn_date.strftime('%Y%m%d')
                amount_str = str(int(amount)) if amount == int(amount) else str(amount)
        
                progress = st.progress(0, text="Submitting...")
                errors = []
        
                for i, file in enumerate(uploaded_files):
                    doc_index = i + 1
                    file_ext = file.name.rsplit('.', 1)[-1].lower()
                    content_type = get_content_type(file.name)
        
                    try:
                        progress.progress(
                            int((i / len(uploaded_files)) * 50),
                            text=f"Registering document {doc_index}..."
                        )
                        result = call_metadata_api(
                            txn_id, txn_date_str, amount_str,
                            category, doc_index, file_ext, content_type, comments
                        )
        
                        progress.progress(
                            int((i / len(uploaded_files)) * 50) + 50,
                            text=f"Uploading document {doc_index} to S3..."
                        )
                        upload_to_presigned_url(result['upload_url'], file.read(), content_type)
        
                    except Exception as e:
                        errors.append(f"Doc {doc_index} ({file.name}): {e}")
        
                progress.progress(100, text="Done!")
        
                if errors:
                    st.warning("Some documents failed:")
                    for err in errors:
                        st.error(err)
                else:
                    st.success(f"✅ Transaction submitted with {len(uploaded_files)} document(s). OCR validation will complete in a few seconds.")
                    st.info("Refresh the Dashboard tab to see updated status.")
