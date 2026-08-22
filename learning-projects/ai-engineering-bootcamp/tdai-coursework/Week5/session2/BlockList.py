# Azure AI Content Safety - Blocklist Management Demo
# This demonstrates how to create custom blocklists for text moderation
# https://learn.microsoft.com/en-us/azure/ai-services/content-safety/how-to/use-blocklist

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from azure.ai.contentsafety import BlocklistClient, ContentSafetyClient
from azure.ai.contentsafety.models import (
    TextBlocklist,
    TextBlocklistItem,
    AddOrUpdateTextBlocklistItemsOptions,
    RemoveTextBlocklistItemsOptions,
    AnalyzeTextOptions
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
import time

# ============================================================
# CONFIGURATION
# ============================================================

from dotenv import load_dotenv
load_dotenv()
KEY = os.getenv("AZURE_CONTENT_SAFETY_KEY")
ENDPOINT = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")

# ============================================================
# Initialize clients
# ============================================================

blocklist_client = BlocklistClient(ENDPOINT, AzureKeyCredential(KEY))
content_safety_client = ContentSafetyClient(ENDPOINT, AzureKeyCredential(KEY))

# ============================================================
# Demo Configuration
# ============================================================

BLOCKLIST_NAME = "DemoBlocklist"
BLOCKLIST_DESCRIPTION = "Demo blocklist for testing custom content moderation"

# ============================================================
# STEP 1: Create or Update a Blocklist
# ============================================================

def step1_create_blocklist():
    print("\n" + "="*80)
    print("STEP 1: CREATE OR UPDATE BLOCKLIST")
    print("="*80)
    print(f"\nCreating blocklist: {BLOCKLIST_NAME}")
    
    try:
        blocklist = blocklist_client.create_or_update_text_blocklist(
            blocklist_name=BLOCKLIST_NAME,
            options=TextBlocklist(
                blocklist_name=BLOCKLIST_NAME,
                description=BLOCKLIST_DESCRIPTION
            ),
        )
        
        print("✓ Blocklist created successfully!")
        print(f"  Name: {blocklist.blocklist_name}")
        print(f"  Description: {blocklist.description}")
        return True
        
    except HttpResponseError as e:
        print(f"❌ Failed to create blocklist")
        if e.error:
            print(f"  Error code: {e.error.code}")
            print(f"  Error message: {e.error.message}")
        return False

# ============================================================
# STEP 2: Add Block Items to the Blocklist
# ============================================================

def step2_add_block_items():
    print("\n" + "="*80)
    print("STEP 2: ADD BLOCK ITEMS")
    print("="*80)
    print("\nAdding custom blocked terms...")
    
    # Define blocked terms - these will be flagged in content
    # Use wildcards (*) to match variations
    block_items = [
        TextBlocklistItem(text="k*ll", description="Violence-related term"),
        TextBlocklistItem(text="h*te", description="Hate speech term"),
        TextBlocklistItem(text="damn", description="Profanity"),
        TextBlocklistItem(text="badword123", description="Custom blocked term"),
        TextBlocklistItem(text="CompetitorBrand", description="Block competitor mentions"),
        TextBlocklistItem(text="leaked_secret", description="Confidential information"),
    ]
    
    try:
        result = blocklist_client.add_or_update_blocklist_items(
            blocklist_name=BLOCKLIST_NAME,
            options=AddOrUpdateTextBlocklistItemsOptions(blocklist_items=block_items)
        )
        
        print(f"✓ Added {len(result.blocklist_items)} items to blocklist:\n")
        for item in result.blocklist_items:
            print(f"  • {item.text}")
            print(f"    ID: {item.blocklist_item_id}")
            print(f"    Description: {item.description}\n")
        
        return True
        
    except HttpResponseError as e:
        print(f"❌ Failed to add block items")
        if e.error:
            print(f"  Error code: {e.error.code}")
            print(f"  Error message: {e.error.message}")
        return False

# ============================================================
# STEP 3: Wait for Blocklist to Propagate
# ============================================================

def step3_wait_for_propagation():
    print("\n" + "="*80)
    print("STEP 3: WAITING FOR BLOCKLIST PROPAGATION")
    print("="*80)
    print("\n⏳ Blocklist changes take ~5 minutes to propagate...")
    print("   (Waiting 10 seconds for demo purposes)")
    
    # In production, wait 5+ minutes after blocklist changes
    # For demo, we'll wait just 10 seconds
    for i in range(10, 0, -1):
        print(f"   {i}...", end=" ", flush=True)
        time.sleep(1)
    print("\n✓ Propagation wait complete")

# ============================================================
# STEP 4: Analyze Text with Blocklist
# ============================================================

def step4_analyze_text_with_blocklist():
    print("\n" + "="*80)
    print("STEP 4: ANALYZE TEXT WITH BLOCKLIST")
    print("="*80)
    
    # Test cases with different blocked terms
    test_cases = [
        {
            "text": "This is a safe message with no blocked terms.",
            "expected": "Should be safe"
        },
        {
            "text": "I h*te you and want to k*ll you!",
            "expected": "Should block: h*te, k*ll"
        },
        {
            "text": "Damn, this is badword123 content.",
            "expected": "Should block: damn, badword123"
        },
        {
            "text": "Check out CompetitorBrand instead!",
            "expected": "Should block: CompetitorBrand"
        },
        {
            "text": "Here is the leaked_secret information.",
            "expected": "Should block: leaked_secret"
        },
        {
            "text": "I hate violence and killing is wrong.",
            "expected": "May or may not block (no wildcards matched)"
        },
    ]
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {idx} ---")
        print(f"Text: \"{test_case['text']}\"")
        print(f"Expected: {test_case['expected']}")
        
        try:
            result = content_safety_client.analyze_text(
                AnalyzeTextOptions(
                    text=test_case['text'],
                    blocklist_names=[BLOCKLIST_NAME],
                    halt_on_blocklist_hit=False  # Continue analysis even if blocked term found
                )
            )
            
            # Check for blocklist matches
            if result.blocklists_match:
                print(f"🚫 BLOCKED - Found {len(result.blocklists_match)} matches:")
                for match in result.blocklists_match:
                    print(f"  • Matched: \"{match.blocklist_item_text}\"")
                    print(f"    Item ID: {match.blocklist_item_id}")
            else:
                print("✓ PASSED - No blocked terms found")
            
            # Also show standard content safety results
            if result.categories_analysis:
                print("\nStandard Safety Analysis:")
                for cat in result.categories_analysis:
                    if cat.severity > 0:
                        print(f"  ⚠ {cat.category}: Severity {cat.severity}")
        
        except HttpResponseError as e:
            print(f"❌ Analysis failed")
            if e.error:
                print(f"  Error: {e.error.message}")

# ============================================================
# STEP 5: List All Blocklists
# ============================================================

def step5_list_blocklists():
    print("\n" + "="*80)
    print("STEP 5: LIST ALL BLOCKLISTS")
    print("="*80)
    
    try:
        blocklists = blocklist_client.list_text_blocklists()
        
        count = 0
        for blocklist in blocklists:
            count += 1
            print(f"\nBlocklist {count}:")
            print(f"  Name: {blocklist.blocklist_name}")
            print(f"  Description: {blocklist.description}")
        
        if count == 0:
            print("No blocklists found")
        else:
            print(f"\n✓ Total blocklists: {count}")
        
    except HttpResponseError as e:
        print(f"❌ Failed to list blocklists")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# STEP 6: Get Specific Blocklist Details
# ============================================================

def step6_get_blocklist_details():
    print("\n" + "="*80)
    print("STEP 6: GET BLOCKLIST DETAILS")
    print("="*80)
    
    try:
        blocklist = blocklist_client.get_text_blocklist(blocklist_name=BLOCKLIST_NAME)
        
        print(f"\nBlocklist Details:")
        print(f"  Name: {blocklist.blocklist_name}")
        print(f"  Description: {blocklist.description}")
        print("✓ Retrieved successfully")
        
    except HttpResponseError as e:
        print(f"❌ Failed to get blocklist")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# STEP 7: List All Block Items in the Blocklist
# ============================================================

def step7_list_block_items():
    print("\n" + "="*80)
    print("STEP 7: LIST ALL BLOCK ITEMS")
    print("="*80)
    
    try:
        block_items = blocklist_client.list_text_blocklist_items(blocklist_name=BLOCKLIST_NAME)
        
        print(f"\nBlock items in '{BLOCKLIST_NAME}':\n")
        count = 0
        for item in block_items:
            count += 1
            print(f"{count}. {item.text}")
            print(f"   ID: {item.blocklist_item_id}")
            print(f"   Description: {item.description}\n")
        
        print(f"✓ Total items: {count}")
        
    except HttpResponseError as e:
        print(f"❌ Failed to list block items")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# STEP 8: Get a Specific Block Item
# ============================================================

def step8_get_specific_block_item():
    print("\n" + "="*80)
    print("STEP 8: GET SPECIFIC BLOCK ITEM")
    print("="*80)
    
    try:
        # First, get the first item ID from the list
        block_items = list(blocklist_client.list_text_blocklist_items(blocklist_name=BLOCKLIST_NAME))
        
        if not block_items:
            print("No block items to retrieve")
            return
        
        first_item_id = block_items[0].blocklist_item_id
        
        # Now get that specific item
        item = blocklist_client.get_text_blocklist_item(
            blocklist_name=BLOCKLIST_NAME,
            blocklist_item_id=first_item_id
        )
        
        print(f"\nRetrieved block item:")
        print(f"  Text: {item.text}")
        print(f"  ID: {item.blocklist_item_id}")
        print(f"  Description: {item.description}")
        print("✓ Retrieved successfully")
        
    except HttpResponseError as e:
        print(f"❌ Failed to get block item")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# STEP 9: Remove a Block Item
# ============================================================

def step9_remove_block_item():
    print("\n" + "="*80)
    print("STEP 9: REMOVE A BLOCK ITEM")
    print("="*80)
    
    try:
        # Get the first item to remove
        block_items = list(blocklist_client.list_text_blocklist_items(blocklist_name=BLOCKLIST_NAME))
        
        if not block_items:
            print("No block items to remove")
            return
        
        item_to_remove = block_items[0]
        print(f"\nRemoving: \"{item_to_remove.text}\" (ID: {item_to_remove.blocklist_item_id})")
        
        blocklist_client.remove_blocklist_items(
            blocklist_name=BLOCKLIST_NAME,
            options=RemoveTextBlocklistItemsOptions(
                blocklist_item_ids=[item_to_remove.blocklist_item_id]
            )
        )
        
        print("✓ Block item removed successfully")
        
    except HttpResponseError as e:
        print(f"❌ Failed to remove block item")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# STEP 10: Delete the Entire Blocklist (Cleanup)
# ============================================================

def step10_delete_blocklist():
    print("\n" + "="*80)
    print("STEP 10: DELETE BLOCKLIST (CLEANUP)")
    print("="*80)
    
    print(f"\nDeleting blocklist: {BLOCKLIST_NAME}")
    
    try:
        blocklist_client.delete_text_blocklist(blocklist_name=BLOCKLIST_NAME)
        print("✓ Blocklist deleted successfully")
        
    except HttpResponseError as e:
        print(f"❌ Failed to delete blocklist")
        if e.error:
            print(f"  Error: {e.error.message}")

# ============================================================
# MAIN EXECUTION
# ============================================================

def run_complete_demo():
    """Run the complete blocklist demonstration"""
    
    print("\n" + "="*80)
    print("AZURE AI CONTENT SAFETY - BLOCKLIST DEMO")
    print("="*80)
    print("\nThis demo will:")
    print("1. Create a custom blocklist")
    print("2. Add blocked terms")
    print("3. Test content against the blocklist")
    print("4. Manage and clean up the blocklist")
    
    input("\nPress Enter to start the demo...")
    
    # Run all steps
    if step1_create_blocklist():
        if step2_add_block_items():
            step3_wait_for_propagation()
            step4_analyze_text_with_blocklist()
    
    step5_list_blocklists()
    step6_get_blocklist_details()
    step7_list_block_items()
    step8_get_specific_block_item()
    step9_remove_block_item()
    
    # Ask before cleanup
    print("\n" + "="*80)
    cleanup = input("\nDelete the demo blocklist? (y/n): ").lower()
    if cleanup == 'y':
        step10_delete_blocklist()
    else:
        print(f"\nBlocklist '{BLOCKLIST_NAME}' kept. Delete it manually later if needed.")
    
    print("\n" + "="*80)
    print("DEMO COMPLETE!")
    print("="*80)
    print("""
KEY TAKEAWAYS:
1. Blocklists allow custom term filtering beyond standard AI detection
2. Use wildcards (*) to match variations (e.g., "k*ll" matches "kill", "killed")
3. Changes take ~5 minutes to propagate across the service
4. Blocklists work alongside standard content safety categories
5. Perfect for: competitor names, confidential terms, domain-specific profanity
    """)

# ============================================================
# QUICK TEST FUNCTIONS
# ============================================================

def quick_test_existing_blocklist():
    """Quick test if you already have a blocklist created"""
    print("\n=== QUICK TEST: Existing Blocklist ===\n")
    
    test_texts = [
        "This is safe content",
        "I h*te this and want to k*ll it",
        "Damn, that's bad",
    ]
    
    for text in test_texts:
        print(f"Testing: \"{text}\"")
        try:
            result = content_safety_client.analyze_text(
                AnalyzeTextOptions(
                    text=text,
                    blocklist_names=[BLOCKLIST_NAME],
                    halt_on_blocklist_hit=False
                )
            )
            
            if result.blocklists_match:
                print(f"  🚫 BLOCKED: {[m.blocklist_item_text for m in result.blocklists_match]}")
            else:
                print(f"  ✓ PASSED")
        except HttpResponseError as e:
            print(f"  ❌ Error: {e.error.message if e.error else str(e)}")
        print()

# ============================================================
# RUN THE DEMO
# ============================================================

if __name__ == "__main__":
    # Choose which mode to run:
    
    # Full demo (recommended for first time)
    run_complete_demo()
    
    # OR quick test if blocklist already exists
    # quick_test_existing_blocklist()