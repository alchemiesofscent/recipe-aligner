#!/usr/bin/env python3
"""
Interactive Equivalence Builder

Usage:
    python scripts/build_equivalences.py

Analyzes aliases to find potential cross-language equivalences and asks for user confirmation.
Builds data/equivalences.json based on user decisions.
"""

import json, re
from difflib import SequenceMatcher
from collections import defaultdict

def load_master():
    with open("data/MASTER.json", "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_alias_text(text):
    """Normalize alias text for matching"""
    # Remove common qualifiers
    text = re.sub(r'\s*\([^)]*\)', '', text)  # Remove parentheticals
    text = re.sub(r'\s*(if\s+\w+)', '', text)  # Remove "if nꜤr" type qualifiers
    
    # Normalize botanical terms
    text = re.sub(r'\s+species?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+berries?$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+resin$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+tree$', '', text, flags=re.IGNORECASE)
    
    # Basic cleanup
    text = re.sub(r'[^\w\s]', '', text)
    text = ' '.join(text.split())
    return text.lower().strip()

def find_similar_aliases(aliases, threshold=0.7):
    """Find groups of similar alias variant_labels"""
    # Normalize all aliases
    normalized_aliases = []
    for alias in aliases:
        if alias.get("language") == "en":  # Only match English aliases
            normalized = normalize_alias_text(alias["variant_label"])
            if len(normalized) > 2:  # Skip very short terms
                normalized_aliases.append({
                    "original": alias,
                    "normalized": normalized,
                    "ingredient_id": alias["ingredient_id"]
                })
    
    # Find similar groups
    potential_groups = defaultdict(list)
    processed = set()
    
    for i, alias1 in enumerate(normalized_aliases):
        if i in processed:
            continue
            
        group = [alias1]
        processed.add(i)
        
        for j, alias2 in enumerate(normalized_aliases):
            if j <= i or j in processed:
                continue
                
            similarity = SequenceMatcher(None, alias1["normalized"], alias2["normalized"]).ratio()
            
            if similarity > threshold:
                group.append(alias2)
                processed.add(j)
        
        if len(group) > 1:
            # Create a canonical name from the most common/simple term
            terms = [a["normalized"] for a in group]
            canonical = min(terms, key=len)  # Use shortest term as canonical
            potential_groups[canonical] = group
    
    return potential_groups

def build_equivalences_interactively():
    print("Interactive Equivalence Builder")
    print("=" * 50)
    
    master = load_master()
    ingredients = {i["ingredient_id"]: i for i in master.get("ingredients", [])}
    aliases = master.get("aliases", [])
    
    print(f"Analyzing {len(aliases)} aliases from {len(ingredients)} ingredients...")
    
    potential_groups = find_similar_aliases(aliases)
    
    if not potential_groups:
        print("No potential equivalence groups found.")
        return
    
    print(f"Found {len(potential_groups)} potential equivalence groups:")
    
    approved_groups = []
    
    for canonical_name, group in potential_groups.items():
        print(f"\n--- Potential group: '{canonical_name}' ---")
        
        # Show ingredients and their aliases
        ingredient_info = {}
        for alias_info in group:
            ing_id = alias_info["ingredient_id"]
            ingredient = ingredients[ing_id]
            
            if ing_id not in ingredient_info:
                ingredient_info[ing_id] = {
                    "ingredient": ingredient,
                    "aliases": []
                }
            ingredient_info[ing_id]["aliases"].append(alias_info["original"]["variant_label"])
        
        print("Ingredients that would be grouped:")
        for ing_id, info in ingredient_info.items():
            ing = info["ingredient"]
            lang = ing.get("language", "unknown")
            aliases_str = ", ".join(info["aliases"])
            print(f"  {ing['slug']}: {ing['label']} ({lang}) - aliases: {aliases_str}")
        
        # Ask user decision
        while True:
            choice = input("Create equivalence group? (y/n/s to skip): ").strip().lower()
            
            if choice == 'y':
                # Ask for canonical name
                suggested_name = canonical_name
                final_name = input(f"Canonical name [{suggested_name}]: ").strip()
                if not final_name:
                    final_name = suggested_name
                
                # Ask for confidence level
                confidence = input("Confidence level (high/medium/low) [medium]: ").strip()
                if not confidence:
                    confidence = "medium"
                
                approved_groups.append({
                    "canonical_name": final_name,
                    "confidence": confidence,
                    "ingredients": [info["ingredient"]["label"] for info in ingredient_info.values()],
                    "slugs": [info["ingredient"]["slug"] for info in ingredient_info.values()],
                    "languages": list(set(info["ingredient"].get("language", "unknown") for info in ingredient_info.values()))
                })
                
                print(f"Added equivalence group: {final_name}")
                break
                
            elif choice == 'n':
                print("Rejected - not creating group")
                break
                
            elif choice == 's':
                print("Skipped")
                break
                
            else:
                print("Please enter y, n, or s")
    
    # Save approved equivalences
    if approved_groups:
        equivalences = {
            "version": "1.0",
            "generated_at": "2025-09-02",
            "method": "interactive_review",
            "equivalence_groups": approved_groups
        }
        
        with open("data/equivalences.json", "w", encoding="utf-8") as f:
            json.dump(equivalences, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Created {len(approved_groups)} equivalence groups")
        print(f"Saved to data/equivalences.json")
        print(f"Next: Update web app to use these equivalences")
    else:
        print("No equivalence groups created")

if __name__ == "__main__":
    build_equivalences_interactively()