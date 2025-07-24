import pdfplumber
import pandas as pd

def extract_table(pdf_path):
    data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    data.append(row)
    return data

def clean_table(data):
    # Find and use the header row
    for i, row in enumerate(data):
        if "Description" in row or "Item" in row:
            header = [col.strip() if col else f"col_{i}" for i, col in enumerate(row)]
            break
    else:
        return pd.DataFrame()  # No valid table

    # Collect rows under the header
    rows = data[i+1:]
    df = pd.DataFrame(rows, columns=header)
    return df

import pdfplumber
import pandas as pd

def extract_table(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n\n--- Page {i+1} ---")
            print("TEXT:\n", page.extract_text())
            table = page.extract_table()
            print("TABLE:\n", table)
            if table:
                return table
    return None

def clean_table(data):
    for i, row in enumerate(data):
        if row and any('desc' in str(cell).lower() for cell in row):
            header = [str(col).strip().lower() if col else f"col_{j}" for j, col in enumerate(row)]
            break
    else:
        return pd.DataFrame()
    rows = data[i+1:]
    return pd.DataFrame(rows, columns=header)

def compare_documents(po_path, invoice_path):
    po_raw = extract_table(po_path)
    inv_raw = extract_table(invoice_path)

    if po_raw is None or inv_raw is None:
        return "❌ Could not extract usable tables from one or both PDFs."

    po_data = clean_table(po_raw)
    inv_data = clean_table(inv_raw)

    if po_data.empty or inv_data.empty:
        return "❌ Could not extract usable tables from one or both PDFs."
    # Normalize all column names
    po_data.columns = [str(col).lower() for col in po_data.columns]
    inv_data.columns = [str(col).lower() for col in inv_data.columns]

    # Print for debug
    print("PO Columns:", po_data.columns.tolist())
    print("Invoice Columns:", inv_data.columns.tolist())

    # Use 'vendor item' and 'item' for matching
    if 'vendor item' not in po_data.columns or 'item' not in inv_data.columns:
        return "❌ Matching columns 'vendor item' or 'item' not found."

    po_data = po_data.set_index('vendor item')
    inv_data = inv_data.set_index('item')

    report = []

    common_items = po_data.index.intersection(inv_data.index)
    only_in_po = po_data.index.difference(inv_data.index)
    only_in_invoice = inv_data.index.difference(po_data.index)

    for item in common_items:
        po_row = po_data.loc[item]
        inv_row = inv_data.loc[item]

        po_qty = str(po_row.get('qty. ordered', '')).strip()
        inv_qty = str(inv_row.get('qty ord', '')).strip()

        if po_qty != inv_qty:
            report.append(f"🔧 Qty Mismatch [{item}]: PO={po_qty}, Invoice={inv_qty}")

        po_price = str(po_row.get('unit cost', '')).strip().replace('£', '')
        inv_price = str(inv_row.get('ext. price', '')).strip().replace('£', '')

        if po_price != inv_price:
            report.append(f"💰 Price Mismatch [{item}]: PO={po_price}, Invoice={inv_price}")

    for item in only_in_po:
        desc = po_data.loc[item].get('description', 'Unknown')
        report.append(f"🗑️ On PO only: [{item}] {desc}")

    for item in only_in_invoice:
        desc = inv_data.loc[item].get('description', 'Unknown')
        report.append(f"➕ On Invoice only: [{item}] {desc}")

    if not report:
        return "✅ PO and Invoice match perfectly!"
    return "\n".join(report)
