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


BUCKET_NAME = "kolshet-home"
TRANSACTIONS_TABLE = "expense_transactions"
LOAN_CONFIG_TABLE = "loan_config"

DOCUMENT_CATEGORIES = ["Legal", "Bank", "Government", "Registration", "Other"]
DOCUMENT_PREFIX = "important-documents/"

SPEND_CATEGORIES = [
    "Token Amount",
    "Home Loan EMI",
    "Interior",
    "Legal/Registration",
    "Maintenance",
    "Other"
]
