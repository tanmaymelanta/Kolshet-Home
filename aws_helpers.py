import boto3
import streamlit as st

def get_s3_client():
    return boto3.client(
        's3',
        region_name=st.secrets["AWS_REGION"],
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
    )

def get_dynamodb_resource():
    return boto3.resource(
        'dynamodb',
        region_name=st.secrets["AWS_REGION"],
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
    )

BUCKET_NAME = "kolshet-home-project"
TRANSACTIONS_TABLE = "expense_transactions"
LOAN_CONFIG_TABLE = "loan_config"

DOCUMENT_CATEGORIES = ["Property Money Transactions", "Banking Loan Documents", "Property Agreement & Registration", "Tax Files"]
DOCUMENT_PREFIX = "Important-Documents/"

SPEND_CATEGORIES = {
    "Property Acquisition": ["Booking Amount", "Down Payment", "Registration", "Stamp Duty", "Brokerage", "Legal Fees"], 
    "Loan & Banking": ["EMI", "EMI Principal", "EMI Interest", "Processing Fee", "Insurance", "Legal Verification"], 
    "Improvement & Interiors": ["Modular Kitchen", "Electrical", "Plumbing", "Painting", "False Ceiling", "AC Installation", "Furniture"], 
    "Maintenance & Society": ["Society Maintenance", "Repairs", "Cleaning", "Security Charges"]
}
