import streamlit as st
import pandas as pd

def emi(principal,rate_of_interest, tenure):
    monthly_roi = rate_of_interest / 12 * 100
    emi = (principal * monthly_roi * (1 + monthly_roi) * tenure) / ((1 + monthly_roi) * tenure - 1)
    return emi

def render():
    st.title("💸 Loan Tracker by Tanmay")
    
    emi_no = []
    for i in range(30):
        emi_no.append(i+1)
    
    df = pd.DataFrame({
        "Month": emi_no
    })
    st.dataframe(df)
