"""
MCP Inventory Server — Demo 4

A FastMCP server that exposes retail inventory tools over stdio.
The client (4_MCP_CustomInventory.py) starts this automatically.

Available tools:
  get_inventory_levels  — current stock for all products
  get_weekly_sales      — units sold last week per product

Usage (standalone test):
  python inventory_server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(name="InventoryServer")

# ── In-memory product catalogue ──────────────────────────────────
INVENTORY = {
    "Moisturizer":     6,
    "Shampoo":         8,
    "Body Spray":     28,
    "Hair Gel":        5,
    "Lip Balm":       12,
    "Skin Serum":      9,
    "Cleanser":       30,
    "Conditioner":     3,
    "Setting Powder": 17,
    "Dry Shampoo":    45,
}

WEEKLY_SALES = {
    "Moisturizer":    22,
    "Shampoo":        18,
    "Body Spray":      3,
    "Hair Gel":        2,
    "Lip Balm":       14,
    "Skin Serum":     19,
    "Cleanser":        4,
    "Conditioner":     1,
    "Setting Powder": 13,
    "Dry Shampoo":    17,
}


@mcp.tool()
def get_inventory_levels() -> dict:
    """Returns current inventory levels for all products."""
    return INVENTORY


@mcp.tool()
def get_weekly_sales() -> dict:
    """Returns number of units sold last week for all products."""
    return WEEKLY_SALES


if __name__ == "__main__":
    mcp.run(transport="stdio")
