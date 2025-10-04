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
import datetime
import os

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
    
    # Build mapping for the web app: { canonical_english: [variants...] }
    # Variants include the canonical English alias and all ingredient labels
    mapping = {}
    for english_name, ingredient_list in english_aliases.items():
        if len(ingredient_list) > 1:  # Only group if multiple ingredients share this alias
            variants = {english_name}
            for ing in ingredient_list:
                label = (ing.get("label") or "").strip()
                if label:
                    variants.add(label)
            mapping[english_name] = sorted(variants)

    # Optionally, sort keys for stability
    mapping = {k: mapping[k] for k in sorted(mapping.keys())}
    return mapping

def main():
    print("Generating equivalences from alias data...")

    equivalences = generate_equivalences()

    # Save mapping to docs/equivalences.json for the web app
    out_path = os.path.join("docs", "equivalences.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(equivalences, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(equivalences)} equivalence groups:")
    
    for key, variants in equivalences.items():
        print(f"  {key}: {len(variants)} variants")
        for v in variants:
            print(f"    - {v}")
    
    print(f"\nSaved to {out_path}")
    print(f"Next: Update web app to load from this file")

if __name__ == "__main__":
    main()
