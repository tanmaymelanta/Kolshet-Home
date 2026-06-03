import pandas as pd
import streamlit as st

def render():
  st.write("loan tracket testing")
  url = "https://docs.google.com/spreadsheets/d/1Sh5-kymrGcPSm8D5e1B1jUB40q0Mel9crvkrBiDFKmc/export?format=csv"
  df = pd.read_csv(url)
  filtered_df = df[df["Status"] == "Paid"].reset_index(drop=True)
  st.dataframe(filtered_df)
  st.dataframe(df)
