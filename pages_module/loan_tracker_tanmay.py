import streamlit as st
import pandas as pd

def emi(principal,rate_of_interest, tenure):
    monthly_roi = rate_of_interest / 12 / 100
    emi = (principal * monthly_roi * (1 + monthly_roi) * tenure) / ((1 + monthly_roi) * tenure - 1)
    return emi

def render():
    st.title("💸 Loan Tracker by Tanmay")
    
    month_no, emi_amount = [], []
    for i in range(360):
        month_no.append(i+1)
        emi_amount.append(emi(principal= 5800000,rate_of_interest= 7.65, tenure= 360))
    
    df = pd.DataFrame({
        "Month": month_no,
        "EMI": emi_amount
    })
    st.dataframe(df, hide_index=True)
