"""Quick script to show what fields exist in the index."""
import os, requests
from dotenv import load_dotenv

load_dotenv()
ENDPOINT = os.getenv("SEARCH_ENDPOINT", "").rstrip("/")
ADMIN_KEY = os.getenv("ADMIN_KEY")
INDEX    = os.getenv("INDEX_NAME")

r = requests.get(
    f"{ENDPOINT}/indexes/{INDEX}?api-version=2024-07-01",
    headers={"api-key": ADMIN_KEY},
    timeout=10,
)
r.raise_for_status()
fields = r.json().get("fields", [])
print(f"Fields in '{INDEX}':\n")
for f in fields:
    print(f"  {f['name']:35s}  {f['type']}")
