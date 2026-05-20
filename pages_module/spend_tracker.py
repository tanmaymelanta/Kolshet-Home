import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import date, datetime
from decimal import Decimal
from aws_helpers import (
    get_dynamodb_resource, get_s3_client,
    TRANSACTIONS_TABLE, SPEND_CATEGORIES, BUCKET_NAME
)

API_URL = "https://a59tnednv1.execute-api.ap-south-1.amazonaws.com/dev"

# ── DynamoDB helpers ──────────────────────────────────────────────────────────
def load_transactions():
    try:
        db = get_dynamodb_resource()
        table = db.Table(TRANSACTIONS_TABLE)
        response = table.scan()
        items = response.get('Items', [])

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
def call_metadata_api(txn_id, txn_date, amount, category, sub_category, doc_index, file_ext, content_type, comments):
    payload = {
        "transaction_id": txn_id,
        "txn_date": txn_date,
        "amount": str(amount),
        "category": category,
        "sub_category": sub_category,
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
    with (tab_dashboard):
        df = load_transactions()

        if not df.empty:
            valid_df = df[df['status'] == 'VALIDATED'].copy()
            invalid_df = df[df['status'] != 'VALIDATED'].copy()
            transactions_df =df[['transaction_id', 'txn_date', 'category', 'comments', 'expected_amount']].drop_duplicates().copy()
            transactions_df['transaction_date'] = transactions_df['txn_date'].apply(lambda d: datetime.strptime(str(d), '%Y%m%d').strftime('%Y-%m-%d') if len(str(d)) == 8 else d[:7])
    
            total_spend = transactions_df['expected_amount'].sum()
            num_txns = len(transactions_df['transaction_id'].unique())
            valid_count = len(valid_df)
            invalid_count = len(invalid_df)
    
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Spend", f"₹{total_spend:,.0f}")
            c2.metric("Transactions", num_txns)
            c3.metric("Valid Documents", valid_count)
            c4.metric("Invalid Documents", invalid_count)
    
            st.markdown("---")
    
            col_left, col_right = st.columns([2, 3])
            with col_left:
                st.markdown("#### Spend by Category")
                cat_df = transactions_df.groupby('category')['expected_amount'].sum().reset_index()
                fig_pie = px.pie(cat_df, values='expected_amount', names='category', color_discrete_sequence=px.colors.qualitative.Set2, hole=0.4)
                fig_pie.update_traces(textposition='outside', texttemplate='%{label}<br>₹%{value:,.0f}', textfont=dict(color='white', size=14))
                fig_pie.update_layout(margin=dict(t=10, b=10, l=20, r=20), height=380, uniformtext_minsize=10, uniformtext_mode='show')
                st.plotly_chart(fig_pie, use_container_width=True)
    
            with col_right:
                st.markdown("#### Daily Spend")
                fig_bar = px.bar(transactions_df, x='transaction_date', y='expected_amount', color_discrete_sequence=["#3498db"], labels={'expected_amount': 'Amount (₹)', 'transaction_date': 'Date'})
                fig_bar.update_layout(margin=dict(t=10, b=10, l=20, r=20), height=380)
                st.plotly_chart(fig_bar, use_container_width=True)
    
            st.markdown("---")
            st.markdown("#### All Transactions")
            status_filter = st.multiselect("Filter by status", options=df['status'].unique().tolist(), default=df['status'].unique().tolist())
            filtered = df[df['status'].isin(status_filter)]
            status_colors = {'VALIDATED': '🟢', 'AMOUNT_MISMATCH': '🟡', 'OCR_FAILED': '🔴', 'PENDING': '⚪'}
            display = filtered[['transaction_id', 'document_id', 'txn_date', 'category', 'sub_category', 'expected_amount', 'status', 'comments', 's3_path']].copy()
            display['status'] = display['status'].apply(lambda s: f"{status_colors.get(s, '')} {s}")
            display['s3_path'] = display['s3_path'].str.split('receipt-vault/').str[1]
            display['txn_date'] = display['txn_date'].apply(lambda d: datetime.strptime(str(d), '%Y%m%d').strftime('%d %b %Y') if len(str(d)) == 8 else d)
            display.columns = ['Txn ID', 'Doc ID', 'Date', 'Category', 'Sub Category', 'Expected (₹)', 'Status', 'Comments', 'Doc Name']
            st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Add transaction tab ───────────────────────────────────────────────────
    with tab_add:
        st.markdown("### New Transaction")
        txn_container = st.container(border=True)
        with txn_container:
            col1, col2 = st.columns(2)
            with col1:
                txn_id = st.text_input("Transaction ID *", placeholder="e.g. T2605161611411488265779")
                category = st.selectbox("Category *", list(SPEND_CATEGORIES.keys()), key="category")
                amount = st.number_input("Amount (₹) *", min_value=0)
            with col2:
                txn_date = st.date_input("Transaction Date *", value=date.today())
                sub_category = st.selectbox("Sub Category *", SPEND_CATEGORIES[category], key=f"subcategory_{category}")
                comments = st.text_area("Comments (optional)", placeholder="e.g. Home token payment to Square Feet Group")
            st.markdown("#### Supporting Documents")
            st.caption("Upload one or more receipts / statements / bills.")
            uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=['pdf', 'jpg', 'jpeg', 'png'])
            submitted = st.button("🚀 Submit Transaction", use_container_width=True)

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
                        progress.progress(int((i / len(uploaded_files)) * 50), text=f"Registering document {doc_index}...")
                        result = call_metadata_api(txn_id, txn_date_str, amount_str, category, sub_category, doc_index, file_ext, content_type, comments)
                        progress.progress(int((i / len(uploaded_files)) * 50) + 50, text=f"Uploading document {doc_index} to S3...")
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
