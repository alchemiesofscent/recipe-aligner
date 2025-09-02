#!/usr/bin/env python3
"""
Auto-generate equivalences from alias data

Usage:
    python scripts/generate_equivalences.py

Analyzes aliases in MASTER.json to find ingredients that share English names,
then builds equivalence groups automatically.
"""

import json
from collections import defaultdict

def load_master():
    with open("data/MASTER.json", "r", encoding="utf-8") as f:
        return json.load(f)

def generate_equivalences():
    master = load_master()
    ingredients = {i["ingredient_id"]: i for i in master.get("ingredients", [])}
    aliases = master.get("aliases", [])
    
    # Group ingredients by shared English aliases
    english_aliases = defaultdict(list)
    
    for alias in aliases:
        if alias.get("language") == "en":
            variant = alias["variant_label"].lower().strip()
            ingredient = ingredients.get(alias["ingredient_id"])
            if ingredient:
                english_aliases[variant].append({
                    "slug": ingredient["slug"],
                    "label": ingredient["label"],
                    "language": ingredient.get("language", "unknown")
                })
    
    # Create equivalence groups for aliases with multiple ingredients
    equivalence_groups = []
    
    for english_name, ingredient_list in english_aliases.items():
        if len(ingredient_list) > 1:  # Only group if multiple ingredients share this alias
            # Determine confidence based on alias specificity
            confidence = "high" if english_name in ["myrrh", "honey", "juniper", "cinnamon"] else "medium"
            
            equivalence_groups.append({
                "canonical_name": english_name,
                "confidence": confidence,
                "ingredients": [ing["label"] for ing in ingredient_list],
                "slugs": [ing["slug"] for ing in ingredient_list],
                "languages": list(set(ing["language"] for ing in ingredient_list)),
                "auto_generated": True
            })
    
    # Sort by number of linked ingredients (most connected first)
    equivalence_groups.sort(key=lambda x: len(x["ingredients"]), reverse=True)
    
    return {
        "version": "auto-generated",
        "generated_at": "2025-09-02",
        "source": "aliases in MASTER.json",
        "equivalence_groups": equivalence_groups
    }

def main():
    print("Generating equivalences from alias data...")
    
    equivalences = generate_equivalences()
    
    # Save to data/equivalences.json
    with open("data/equivalences.json", "w", encoding="utf-8") as f:
        json.dump(equivalences, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(equivalences['equivalence_groups'])} equivalence groups:")
    
    for group in equivalences['equivalence_groups']:
        print(f"  {group['canonical_name']}: {len(group['ingredients'])} ingredients")
        for ing in group['ingredients']:
            print(f"    - {ing}")
    
    print(f"\nSaved to data/equivalences.json")
    print(f"Next: Update web app to load from this file")

if __name__ == "__main__":
    main()