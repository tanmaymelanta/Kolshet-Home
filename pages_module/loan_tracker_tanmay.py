import streamlit as st

def render():
    st.title("💸 Loan Tracker by Tanmay")
    
    tab1, tab2 = st.tabs(["loan config", "emi table"])
    
    with tab1:
        principal = st.number_input("Principal Amount")
        rate_of_interest = st.number_input("Rate of Interest")
        emi = st.number_input("EMI")
