import sys
import os
import streamlit as st
sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Y Square Home Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🏠 Y-Square Home")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "💸 Spend Tracker",
        "📊 Loan Tracker", 
        "📁 Document Hub",
        "🏠 Home Purchase Event Log",
    ],
    label_visibility="collapsed"
)

if page == "💸 Spend Tracker":
    from pages_module.spend_tracker import render
    render()
elif page == "📊 Loan Tracker":
    from pages_module.loan_tracker import render
    render()
elif page == "📁 Document Hub":
    from pages_module.document_hub import render
    render()
elif page == "🏠 Home Purchase Event Log":
    from pages_module.event_log import render
    render()
