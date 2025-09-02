#!/usr/bin/env python3
"""
Simple Ingredient Linking Tool

Usage:
    python scripts/link_ingredients.py diffs/my_diff.json

Shows you new ingredients, suggests existing matches, lets you link them.
Much simpler than the complex system - just handles the core linking problem.
"""

import json, sys
from difflib import SequenceMatcher
import re

def normalize(text):
    """Simple normalization for matching"""
    return re.sub(r'[^\w\s]', '', text.lower().strip())

def load_existing_ingredients():
    """Load existing ingredients from master"""
    try:
        with open("data/MASTER.json", "r", encoding="utf-8") as f:
            master = json.load(f)
        return master.get("ingredients", [])
    except FileNotFoundError:
        return []

def find_similar(new_label, existing_ingredients, threshold=0.6):
    """Find similar existing ingredients"""
    new_norm = normalize(new_label)
    matches = []
    
    for existing in existing_ingredients:
        existing_norm = normalize(existing["label"])
        similarity = SequenceMatcher(None, new_norm, existing_norm).ratio()
        
        if similarity > threshold:
            matches.append({
                "slug": existing["slug"],
                "label": existing["label"],
                "similarity": similarity
            })
    
    return sorted(matches, key=lambda x: x["similarity"], reverse=True)

def process_diff(diff_path):
    """Process a diff file interactively"""
    print(f"Processing: {diff_path}")
    
    # Load diff
    with open(diff_path, "r", encoding="utf-8") as f:
        diff = json.load(f)
    
    # Load existing ingredients
    existing_ingredients = load_existing_ingredients()
    print(f"Found {len(existing_ingredients)} existing ingredients to match against")
    
    new_ingredients = diff.get("ingredients", [])
    if not new_ingredients:
        print("No new ingredients to process")
        return
    
    print(f"\nProcessing {len(new_ingredients)} new ingredients...")
    
    # Track changes
    to_remove = []  # ingredient slugs to remove from diff
    aliases_to_add = []  # aliases to add to diff
    entries_to_update = {}  # old_slug -> new_slug mapping
    
    for ingredient in new_ingredients:
        print(f"\n--- New ingredient: '{ingredient['label']}' (slug: {ingredient['slug']}) ---")
        
        # Find similar existing ingredients
        matches = find_similar(ingredient["label"], existing_ingredients)
        
        if not matches:
            print("No similar ingredients found - keeping as new")
            continue
        
        print("Similar existing ingredients:")
        for i, match in enumerate(matches[:5]):  # Show top 5
            print(f"  {i+1}. {match['slug']}: {match['label']} ({match['similarity']:.2f})")
        
        # Ask user
        while True:
            choice = input("Link to existing? (1-5, 'n' for new ingredient): ").strip()
            
            if choice.lower() == 'n':
                print("Keeping as new ingredient")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(matches[:5]):
                # Link to existing
                chosen = matches[int(choice) - 1]
                print(f"Linking '{ingredient['label']}' to existing '{chosen['slug']}'")
                
                # Mark ingredient for removal
                to_remove.append(ingredient["slug"])
                
                # Add alias
                aliases_to_add.append({
                    "ingredient_slug": chosen["slug"],
                    "variant_label": ingredient["label"],
                    "language": ingredient.get("language"),
                    "source": "linked by tool"
                })
                
                # Mark entries for updating
                entries_to_update[ingredient["slug"]] = chosen["slug"]
                break
            else:
                print("Invalid choice")
    
    # Apply changes
    if to_remove or aliases_to_add:
        print(f"\nApplying changes:")
        print(f"  Removing {len(to_remove)} ingredients (linked to existing)")
        print(f"  Adding {len(aliases_to_add)} aliases")
        
        # Remove linked ingredients
        diff["ingredients"] = [i for i in diff["ingredients"] if i["slug"] not in to_remove]
        
        # Add aliases
        if "aliases" not in diff:
            diff["aliases"] = []
        diff["aliases"].extend(aliases_to_add)
        
        # Update entries
        for entry in diff.get("entries", []):
            if entry["ingredient_slug"] in entries_to_update:
                old_slug = entry["ingredient_slug"]
                new_slug = entries_to_update[old_slug]
                entry["ingredient_slug"] = new_slug
                print(f"  Updated entry: {old_slug} -> {new_slug}")
        
        # Save
        with open(diff_path + ".backup", "w", encoding="utf-8") as f:
            json.dump(json.load(open(diff_path, "r", encoding="utf-8")), f, indent=2)
        
        with open(diff_path, "w", encoding="utf-8") as f:
            json.dump(diff, f, ensure_ascii=False, indent=2)
        
        print(f"Done! Original saved as {diff_path}.backup")
        print("\nNext: python scripts/validate_diff.py " + diff_path)
    else:
        print("No changes made")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/link_ingredients.py diffs/my_diff.json")
        sys.exit(1)
    
    process_diff(sys.argv[1])