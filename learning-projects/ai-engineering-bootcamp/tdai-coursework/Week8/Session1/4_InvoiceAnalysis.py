from dotenv import load_dotenv
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# -------------------------------------------------------
# Demo 3: Invoice Analyser — Azure Document Intelligence
#
# Uses the prebuilt-invoice model to extract structured
# data from invoice documents (PDF or image).
#
# Fields extracted automatically:
#   Vendor & customer details   Invoice ID, dates
#   Line items (qty, price)     Totals, tax, subtotal
#   Billing / shipping address  Purchase order number
#
# No training or schema required — the model already
# understands invoices out of the box.
#
# Usage:
#   python 3_InvoiceAnalysis.py
# -------------------------------------------------------
load_dotenv()

ENDPOINT     = os.getenv("DOC_INTELLIGENCE_ENDPOINT", "").rstrip("/")
KEY          = os.getenv("DOC_INTELLIGENCE_KEY")
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
INVOICES_DIR = os.path.join(SCRIPT_DIR, "sample_invoices")


def get_client():
    return DocumentIntelligenceClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
    )


def analyse_invoice(client, file_path: str):
    """Send a local invoice file to the prebuilt-invoice model."""
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    ext = os.path.splitext(file_path)[1].lower()
    content_type = "application/pdf" if ext == ".pdf" else "application/octet-stream"

    poller = client.begin_analyze_document(
        "prebuilt-invoice",
        body=file_bytes,
        content_type=content_type,
        locale="en-US",
    )
    return poller.result()


# -------------------------------------------------------
# Helper functions — the SDK uses typed value attributes:
#   value_string   -> plain text fields
#   value_date     -> date fields (returns datetime.date)
#   value_number   -> numeric fields
#   value_currency -> currency (.amount, .currency_symbol)
#   value_array    -> array fields (e.g. line items)
#   value_object   -> object fields (sub-fields of an item)
#   content        -> raw text as it appears on the document
# -------------------------------------------------------
def s(fields, name):
    """Return string field value or dash."""
    f = fields.get(name)
    if not f:
        return "-"
    return f.value_string or f.content or "-"


def d(fields, name):
    """Return date field value as string or dash."""
    f = fields.get(name)
    if not f:
        return "-"
    return str(f.value_date) if f.value_date else (f.content or "-")


def addr(fields, name):
    """Return address content on one line or dash."""
    f = fields.get(name)
    if not f or not f.content:
        return "-"
    return f.content.replace("\n", ", ").strip()


def money(fields, name):
    """Return formatted currency string like $110.00."""
    f = fields.get(name)
    if not f or not f.value_currency:
        return "-"
    cv = f.value_currency
    symbol = cv.currency_symbol or "$"
    return f"{symbol}{cv.amount:.2f}" if cv.amount is not None else "-"


def print_invoice(result, filename: str):
    print(f"\n{'=' * 60}")
    print(f"  {filename}")
    print(f"{'=' * 60}")

    if not result.documents:
        print("  No invoice detected.\n")
        return

    for i, doc in enumerate(result.documents, 1):
        if len(result.documents) > 1:
            print(f"\n  --- Invoice {i} of {len(result.documents)} ---")

        fields = doc.fields or {}

        # Header
        print()
        print(f"  Vendor       : {s(fields, 'VendorName')}")
        print(f"  Customer     : {s(fields, 'CustomerName')}")
        print(f"  Customer ID  : {s(fields, 'CustomerId')}")
        print()
        print(f"  Invoice #    : {s(fields, 'InvoiceId')}")
        print(f"  Invoice Date : {d(fields, 'InvoiceDate')}")
        print(f"  Due Date     : {d(fields, 'DueDate')}")
        print(f"  P.O. Number  : {s(fields, 'PurchaseOrder')}")

        # Addresses
        bill = addr(fields, "BillingAddress")
        ship = addr(fields, "ShippingAddress")
        if bill != "-" or ship != "-":
            print()
            if bill != "-":
                print(f"  Bill To      : {bill}")
            if ship != "-":
                print(f"  Ship To      : {ship}")

        # Line Items
        items_field = fields.get("Items")
        items_array = getattr(items_field, "value_array", None) if items_field else None

        if items_array:
            print()
            print(f"  {'DESCRIPTION':<35} {'QTY':>5}  {'UNIT':>10}  {'TOTAL':>10}")
            print(f"  {'-'*65}")
            for item in items_array:
                sub   = item.value_object or {}
                desc  = s(sub, "Description")
                qty_f = sub.get("Quantity")
                qty   = str(int(qty_f.value_number)) if qty_f and qty_f.value_number else "-"
                unit  = money(sub, "UnitPrice")
                total = money(sub, "Amount")
                if len(desc) > 33:
                    desc = desc[:30] + "..."
                print(f"  {desc:<35} {qty:>5}  {unit:>10}  {total:>10}")

        # Totals
        subtotal = money(fields, "SubTotal")
        tax      = money(fields, "TotalTax")
        total    = money(fields, "InvoiceTotal")
        print()
        if subtotal != "-": print(f"  {'Subtotal':<20} {subtotal:>10}")
        if tax      != "-": print(f"  {'Tax':<20} {tax:>10}")
        if total    != "-": print(f"  {'TOTAL':<20} {total:>10}")

    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 60)
    print("  Invoice Analyser")
    print("  Azure Document Intelligence -- prebuilt-invoice")
    print("=" * 60)
    print()

    client = get_client()

    supported = (".pdf", ".jpg", ".jpeg", ".png")
    invoices = [
        f for f in os.listdir(INVOICES_DIR)
        if f.lower().endswith(supported)
    ]

    if not invoices:
        print(f"No invoices found in {INVOICES_DIR}")
        return

    print(f"Found {len(invoices)} invoice(s) to analyse.\n")

    for filename in sorted(invoices):
        path = os.path.join(INVOICES_DIR, filename)
        print(f"Analysing: {filename}...", end=" ", flush=True)
        result = analyse_invoice(client, path)
        print("done.")
        print_invoice(result, filename)

    print("Key Concepts:")
    print("  prebuilt-invoice understands invoices out of the box --")
    print("  no training, no schema, no configuration required.")
    print()
    print("  It extracts 23+ fields: vendor, customer, dates, P.O.")
    print("  number, line items with qty/price, and totals.")
    print()
    print("  Works on PDFs and images. Confidence scores on every")
    print("  field show how certain the model is about each value.")
    print()


if __name__ == "__main__":
    main()
