import streamlit as st
import uuid
from datetime import datetime
from decimal import Decimal
from aws_helpers import get_dynamodb_resource

# ----------------------------
# DynamoDB Config
# ----------------------------
TABLE_NAME = "home_events"
def get_table():
    db = get_dynamodb_resource()
    return db.Table(TABLE_NAME)

# ----------------------------
# Render
# ----------------------------
def render():
    st.title("🏠 Home Purchase Event Log")
    # ----------------------------
    # Event Entry Form
    # ----------------------------
    with st.expander("➕ Add New Event", expanded=True):
        col1, col2 = st.columns(2)
        event_date = col1.date_input("Event Date", value=datetime.today())
        amount = col2.number_input("Amount (₹)", step=0)
        remarks = st.text_area("Remarks", placeholder="Additional details...")
        if st.button("Save Event"):
            try:
                table = get_table()
                event_id = str(uuid.uuid4())
                item = {
                    "event_id": event_id,
                    "event_date": str(event_date),
                    "amount": Decimal(str(amount)),
                    "remarks": remarks,
                }
                table.put_item(Item=item)
                st.success("Event saved successfully.")
            except Exception as e:
                st.error(f"Could not save event: {e}")
    
    # ----------------------------
    # Load Events
    # ----------------------------
    st.divider()
    st.subheader("📅 Event Timeline")
    try:
        table = get_table()
        response = table.scan()
        events = response.get("Items", [])
        events = sorted(events, key=lambda x: x["event_date"])
    except Exception as e:
        st.error(f"Could not load events: {e}")
        return
    
    if not events:
        st.info("No events found.")
    else:
        st.divider()
        for e in events:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 2])
                c1.write("**Date**")
                c1.write(e["event_date"])
                c2.write("****")
                c2.write(e["remarks"])
                c3.write("****")
                c3.write(f'**₹{e["amount"]}**')
