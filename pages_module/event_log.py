import streamlit as st
import uuid
from datetime import datetime
from decimal import Decimal
from aws_helpers import get_dynamodb_resource

# ----------------------------
# DynamoDB Config
# ----------------------------
TABLE_NAME = "home_event"

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
        with col1:
            event_date = st.date_input(
                "Event Date",
                value=datetime.today()
            )
            event_type = st.selectbox(
                "Event Type",
                [
                    "TOKEN_PAYMENT",
                    "BOOKING_AMOUNT",
                    "LOGIN_CHARGES",
                    "LOAN_APPLICATION",
                    "SANCTION_LETTER",
                    "REGISTRATION",
                    "OCR_PAYMENT",
                    "FIRST_DISBURSEMENT",
                    "DEMAND_LETTER",
                    "EMI_START",
                    "PREPAYMENT",
                    "FORECLOSURE",
                    "POSSESSION",
                    "REFUND",
                    "OTHER"
                ]
            )
            event_name = st.text_input(
                "Event Name",
                placeholder="Token Amount Paid"
            )
        with col2:
            amount = st.number_input(
                "Amount (₹)",
                min_value=0.0,
                step=1000.0
            )
            party_name = st.text_input(
                "Party Name",
                placeholder="L&T Finance / SBI / Builder"
            )
            status = st.selectbox(
                "Status",
                ["COMPLETED", "PLANNED", "PENDING", "CANCELLED"]
            )
        remarks = st.text_area(
            "Remarks",
            placeholder="Additional details..."
        )
        if st.button("Save Event"):
            try:
                table = get_table()
                event_id = str(uuid.uuid4())
                item = {
                    "event_id": event_id,
                    "event_date": str(event_date),
                    "event_type": event_type,
                    "event_name": event_name,
                    "status": status,
                    "amount": Decimal(str(amount)),
                    "party_name": party_name,
                    "remarks": remarks,
                    "created_at": datetime.utcnow().isoformat()
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
        total_paid = sum(
            float(e.get("amount", 0))
            for e in events
            if e.get("status") == "COMPLETED"
        )
        st.metric(
            "Total Amount Recorded",
            f"₹ {total_paid:,.0f}"
        )
        st.divider()
        for e in events:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 2])
                with c1:
                    st.write("**Date**")
                    st.write(e["event_date"])
                with c2:
                    st.write(f"**{e.get('event_name', '')}**")
                    st.caption(e.get("event_type", ""))
                    if e.get("remarks"):
                        st.write(e["remarks"])
                with c3:
                    st.write(f"**₹ {float(e.get('amount', 0)):,.0f}**")
                    st.write(e.get("status", ""))
                    if e.get("party_name"):
                        st.caption(e["party_name"])
