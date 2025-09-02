#!/usr/bin/env python3
"""
Remove entries from MASTER.json based on a diff file.

Usage:
    python scripts/remove_diff.py data/MASTER.json diffs/my_diff.json [removed_by]

- Removes entries that match (recipe_slug, ingredient_slug, amount_raw, preparation)
- Removes aliases that match (ingredient_slug, variant_label)  
- Removes ingredients if no entries or aliases reference them
- Removes recipes if no entries reference them
- Safe: won't remove if other data depends on it
"""

import json, sys, datetime

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def remove_diff(master_path, diff_path, removed_by="manual"):
    master = load(master_path)
    diff = load(diff_path)
    
    # Build lookup maps
    recipes_by_slug = {r["slug"]: r for r in master["recipes"]}
    ingredients_by_slug = {i["slug"]: i for i in master["ingredients"]}
    
    removed_entries = 0
    removed_aliases = 0
    removed_ingredients = 0
    removed_recipes = 0
    
    # 1) Remove matching entries
    original_entries = master["entries"][:]
    master["entries"] = []
    
    for entry in original_entries:
        # Find the recipe and ingredient for this entry
        recipe = next((r for r in master["recipes"] if r["recipe_id"] == entry["recipe_id"]), None)
        ingredient = next((i for i in master["ingredients"] if i["ingredient_id"] == entry["ingredient_id"]), None)
        
        if not recipe or not ingredient:
            # Keep entry if we can't find recipe/ingredient (shouldn't happen)
            master["entries"].append(entry)
            continue
            
        # Check if this entry matches any in the diff
        should_remove = False
        for diff_entry in diff.get("entries", []):
            if (recipe["slug"] == diff_entry["recipe_slug"] and 
                ingredient["slug"] == diff_entry["ingredient_slug"] and
                (entry.get("amount_raw") or "") == (diff_entry.get("amount_raw") or "") and
                (entry.get("preparation") or "") == (diff_entry.get("preparation") or "")):
                should_remove = True
                break
                
        if should_remove:
            removed_entries += 1
            print(f"Removed entry: {recipe['slug']} → {ingredient['slug']}")
        else:
            master["entries"].append(entry)
    
    # 2) Remove matching aliases
    original_aliases = master["aliases"][:]
    master["aliases"] = []
    
    for alias in original_aliases:
        ingredient = next((i for i in master["ingredients"] if i["ingredient_id"] == alias["ingredient_id"]), None)
        
        if not ingredient:
            master["aliases"].append(alias)
            continue
            
        # Check if this alias matches any in the diff
        should_remove = False
        for diff_alias in diff.get("aliases", []):
            if (ingredient["slug"] == diff_alias["ingredient_slug"] and 
                alias["variant_label"] == diff_alias["variant_label"]):
                should_remove = True
                break
                
        if should_remove:
            removed_aliases += 1
            print(f"Removed alias: {ingredient['slug']} → '{alias['variant_label']}'")
        else:
            master["aliases"].append(alias)
    
    # 3) Remove ingredients if no longer referenced
    ingredient_ids_in_use = set()
    
    # Check entries
    for entry in master["entries"]:
        ingredient_ids_in_use.add(entry["ingredient_id"])
    
    # Check aliases  
    for alias in master["aliases"]:
        ingredient_ids_in_use.add(alias["ingredient_id"])
    
    original_ingredients = master["ingredients"][:]
    master["ingredients"] = []
    
    for ingredient in original_ingredients:
        # Check if this ingredient is in the diff and not in use
        should_remove = False
        for diff_ingredient in diff.get("ingredients", []):
            if (ingredient["slug"] == diff_ingredient["slug"] and 
                ingredient["ingredient_id"] not in ingredient_ids_in_use):
                should_remove = True
                break
                
        if should_remove:
            removed_ingredients += 1
            print(f"Removed unused ingredient: {ingredient['slug']} ({ingredient['label']})")
        else:
            master["ingredients"].append(ingredient)
    
    # 4) Remove recipes if no longer referenced
    recipe_ids_in_use = {entry["recipe_id"] for entry in master["entries"]}
    
    original_recipes = master["recipes"][:]
    master["recipes"] = []
    
    for recipe in original_recipes:
        # Check if this recipe is in the diff and not in use
        should_remove = False
        for diff_recipe in diff.get("recipes", []):
            if (recipe["slug"] == diff_recipe["slug"] and 
                recipe["recipe_id"] not in recipe_ids_in_use):
                should_remove = True
                break
                
        if should_remove:
            removed_recipes += 1
            print(f"Removed unused recipe: {recipe['slug']} ({recipe['label']})")
        else:
            master["recipes"].append(recipe)
    
    print(f"\n✅ Removal complete:")
    print(f"   • {removed_entries} entries removed")
    print(f"   • {removed_aliases} aliases removed") 
    print(f"   • {removed_ingredients} ingredients removed")
    print(f"   • {removed_recipes} recipes removed")
    
    if removed_entries + removed_aliases + removed_ingredients + removed_recipes == 0:
        print("   • No matching items found to remove")
    
    save(master_path, master)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: remove_diff.py data/MASTER.json diffs/your_diff.json [removed_by]")
        sys.exit(1)
    
    print(f"🗑️  Removing diff: {sys.argv[2]}")
    print(f"📁 From master: {sys.argv[1]}")
    
    remove_diff(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "manual")