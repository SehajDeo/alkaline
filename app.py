import streamlit as st
import openai
import pdfplumber
import os
import pandas as pd  # add pandas import
from dotenv import load_dotenv

load_dotenv()  # load environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="PO vs Invoice - GPT Comparator", layout="wide")
st.title("📄 PO vs Invoice - GPT-Powered Comparator")

po_file = st.file_uploader("Upload PO PDF", type="pdf")
inv_file = st.file_uploader("Upload Invoice PDF", type="pdf")

def extract_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def build_prompt(po_text, inv_text):
    return f"""
You're comparing a purchase order and an invoice. Identify only the mismatched items.
Match items by their item number or description. Focus on differences in:
- Quantity Ordered vs Delivered
- Unit Price
- Missing or extra items

Return a markdown table with columns:
Item Number | Description | Qty PO | Qty Invoice | Unit Price PO | Unit Price Invoice | Status

--- PURCHASE ORDER ---
{po_text}

--- INVOICE ---
{inv_text}
"""

@st.cache_data(show_spinner="Asking GPT...")
def get_comparison(po_text, inv_text):
    prompt = build_prompt(po_text, inv_text)
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a careful procurement assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content

def markdown_to_df(md_text):
    # Split lines and remove markdown table header/footer lines
    lines = [line.strip() for line in md_text.splitlines() if line.strip()]
    # Remove table separators like ----
    lines = [line for line in lines if not line.startswith('|---')]
    # Convert to list of lists for DataFrame
    rows = []
    for line in lines:
        # Remove leading/trailing pipe and split on pipe
        if line.startswith('|') and line.endswith('|'):
            row = [col.strip() for col in line[1:-1].split('|')]
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    # First row is header
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df

if po_file and inv_file:
    with st.spinner("Extracting text from PDFs..."):
        po_text = extract_text(po_file)
        inv_text = extract_text(inv_file)

    if not po_text.strip() or not inv_text.strip():
        st.error("Could not extract readable text from one of the PDFs. Make sure it's not scanned.")
    else:
        raw_result = get_comparison(po_text, inv_text)

        # Parse markdown table to DataFrame and deduplicate
        df_result = markdown_to_df(raw_result)
        df_result = df_result.drop_duplicates()

        if df_result.empty:
            st.info("No mismatches found!")
        else:
            st.markdown("### 🔍 Mismatch Report")
            st.dataframe(df_result)

            csv = df_result.to_csv(index=False)
            st.download_button("Download CSV", data=csv.encode("utf-8"), file_name="mismatches.csv", mime="text/csv")