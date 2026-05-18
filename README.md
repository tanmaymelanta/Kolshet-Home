# Kolshet Home Dashboard

Personal dashboard to track home loan, expenses, and documents for the Kolshet property.

## Features
- 📊 **Loan Tracker** — EMI breakdown, amortization chart, repayment progress
- 💸 **Spend Tracker** — Log transactions with receipts, category-wise visualization
- 📁 **Document Hub** — Store and access important property documents

## Local Setup

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Fill in your AWS credentials and API URL in secrets.toml
streamlit run app.py
```

## AWS Setup Required

### DynamoDB Tables
1. `expense_transactions` — PK: `transaction_id` (String), SK: `document_id` (String)
2. `loan_config` — PK: `config_id` (String)

### S3 Bucket: `kolshet-home`
```
kolshet-home/
    receipt-vault/
        raw/
        validated/
        rejected/
    important-documents/
        Legal/
        Bank/
        Government/
        Registration/
        Other/
```

### IAM User for Streamlit
Create a dedicated IAM user with this policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::kolshet-home",
        "arn:aws:s3:::kolshet-home/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-south-1:*:table/expense_transactions",
        "arn:aws:dynamodb:ap-south-1:*:table/loan_config"
      ]
    }
  ]
}
```

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (private repo recommended)
2. Go to share.streamlit.io → New app
3. Select repo, branch, set `app.py` as main file
4. Under **Advanced settings → Secrets**, paste your secrets (from secrets.toml.template)
5. Deploy

## Secrets Required
```toml
AWS_ACCESS_KEY_ID = "..."
AWS_SECRET_ACCESS_KEY = "..."
AWS_REGION = "ap-south-1"
API_GATEWAY_URL = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/dev"
```
