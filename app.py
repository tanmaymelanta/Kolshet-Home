import sys
import os

# Ensure project root is in path (needed for Streamlit Cloud)
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="Kolshet Home Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🏠 Kolshet Home")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Loan Tracker", "💸 Spend Tracker", "📁 Document Hub"],
    label_visibility="collapsed"
)

if page == "📊 Loan Tracker":
    from pages_module.loan_tracker import render
    render()
elif page == "💸 Spend Tracker":
    from pages_module.spend_tracker import render
    render()
elif page == "📁 Document Hub":
    from pages_module.document_hub import render
    render()
