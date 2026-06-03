import pandas as pd
import streamlit as st
import plotly.express as px

def render():
  st.write("loan tracket testing")
  url = "https://docs.google.com/spreadsheets/d/1Sh5-kymrGcPSm8D5e1B1jUB40q0Mel9crvkrBiDFKmc/export?format=csv"
  df = pd.read_csv(url)
  filtered_df = df[df["Status"] == "Paid"].reset_index(drop=True)
  
  money_cols = ["Opening Balance", "Interest Paid", "Principal Paid", "Closing Balance", "Loan Added", "EMI Paid"]
  for col in money_cols:
    filtered_df[col] = (filtered_df[col].astype(str).str.replace("₹", "", regex=False).str.replace(",", "", regex=False).str.strip())
    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")

  current_balance = filtered_df["Closing Balance"].iloc[-1]
  total_interest_paid = filtered_df["Interest Paid"].sum()
  total_principal_paid = filtered_df["Principal Paid"].sum()
  col1, col2, col3 = st.columns(3)
  col1.metric("Outstanding Balance", f"₹{current_balance:,.0f}")
  col2.metric("Principal Paid", f"₹{total_principal_paid:,.0f}")
  col3.metric("Interest Paid", f"₹{total_interest_paid:,.0f}")

  loan_amount = filtered_df["Loan Added"].sum()
  paid = filtered_df["Principal Paid"].sum() + filtered_df["Extra Principal Paid"].sum()
  progress = paid / loan_amount
  st.progress(progress)
  st.write(f"{progress:.1%} of principal repaid",use_container_width=True)

  st.divider()
  fig = px.line(filtered_df, x="Month-Year", y="Closing Balance", markers=True, title="Outstanding Balance Over Time")
  fig.update_layout(xaxis_title="Month", yaxis_title="Outstanding Balance (₹)",hovermode="x unified")
  st.plotly_chart(fig, use_container_width=True) 

  st.divider()
  fig = px.area(filtered_df, x="Month-Year", y=["Interest Paid", "Principal Paid"], title="EMI Composition")
  st.plotly_chart(fig, use_container_width=True)

  st.divider()
  st.dataframe(df)
