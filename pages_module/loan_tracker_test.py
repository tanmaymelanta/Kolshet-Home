import pandas as pd
import streamlit as st

def render():
  st.write("loan tracket testing")
  url = "https://docs.google.com/spreadsheets/d/1Sh5-kymrGcPSm8D5e1B1jUB40q0Mel9crvkrBiDFKmc/export?format=csv"
  df = pd.read_csv(url)
  filtered_df = df[df["Status"] == "Paid"].reset_index(drop=True)

  st.write(df.dtypes)
  st.write(df["Status"].unique())
  filtered_df = df[df["Status"].astype(str).str.strip() == "Paid"]
  st.write(filtered_df.head())

  current_balance = filtered_df["Closing Balance"].iloc[-1]
  total_interest_paid = filtered_df["Interest Paid"].sum()
  total_principal_paid = filtered_df["Principal Paid"].sum()

  col1, col2, col3 = st.columns(3)
  col1.metric("Outstanding Balance", f"₹{current_balance:,.0f}")
  col2.metric("Principal Paid", f"₹{total_principal_paid:,.0f}")
  col3.metric("Interest Paid", f"₹{total_interest_paid:,.0f}")
  
  st.dataframe(df)
