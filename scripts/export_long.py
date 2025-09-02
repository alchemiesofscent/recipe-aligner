#!/usr/bin/env python3
"""
Export MASTER.json to long-format JSON for the web app.

Flattens the relational structure into a simple array of recipe-ingredient rows
with human-readable labels instead of numeric IDs.

Usage:
    python scripts/export_long.py data/MASTER.json docs/kyphi_long.json
"""

import json, sys, os
from collections import Counter

def export(master_path, out_path):
    print("🔄 Kyphi Long Export")
    print("=" * 50)
    
    print(f"📁 Loading master: {master_path}")
    
    if not os.path.exists(master_path):
        print(f"❌ Error: Master file not found: {master_path}")
        sys.exit(1)
        
    try:
        with open(master_path, "r", encoding="utf-8") as f:
            m = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in master file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading master file: {e}")
        sys.exit(1)
    
    # Build lookup tables
    print("🗂️  Building lookup tables...")
    recipes = {r["recipe_id"]: r for r in m.get("recipes", [])}
    ingredients = {i["ingredient_id"]: i for i in m.get("ingredients", [])}
    entries = m.get("entries", [])
    
    # Build alias lookup for ingredients
    aliases = m.get("aliases", [])
    ingredient_aliases = {}
    for alias in aliases:
        ingredient_id = alias["ingredient_id"]
        if ingredient_id not in ingredient_aliases:
            ingredient_aliases[ingredient_id] = []
        # Collect English aliases for search
        if alias.get("language") == "en":
            ingredient_aliases[ingredient_id].append(alias["variant_label"])
    
    print(f"📊 Master contains:")
    print(f"   • {len(recipes)} recipes")
    print(f"   • {len(ingredients)} ingredients")
    print(f"   • {len(m.get('aliases', []))} aliases")
    print(f"   • {len(entries)} entries")
    
    if len(entries) == 0:
        print("⚠️  Warning: No entries found - output will be empty")
    
    # Check for missing references
    missing_recipes = []
    missing_ingredients = []
    
    print("\n🔍 Validating references...")
    for i, e in enumerate(entries):
        if e["recipe_id"] not in recipes:
            missing_recipes.append(e["recipe_id"])
        if e["ingredient_id"] not in ingredients:
            missing_ingredients.append(e["ingredient_id"])
    
    if missing_recipes:
        print(f"❌ Error: {len(missing_recipes)} entries reference missing recipes: {set(missing_recipes)}")
        sys.exit(1)
    if missing_ingredients:
        print(f"❌ Error: {len(missing_ingredients)} entries reference missing ingredients: {set(missing_ingredients)}")
        sys.exit(1)
        
    print("✅ All references valid")
    
    # Build alias lookup for ingredients
    aliases = m.get("aliases", [])
    ingredient_aliases = {}
    for alias in aliases:
        ingredient_id = alias["ingredient_id"]
        if ingredient_id not in ingredient_aliases:
            ingredient_aliases[ingredient_id] = []
        # Collect English aliases for search
        if alias.get("language") == "en":
            ingredient_aliases[ingredient_id].append(alias["variant_label"])
    
    # Build rows
    print("\n📝 Building long-format rows...")
    rows = []
    recipe_counts = Counter()
    ingredient_counts = Counter()
    
    for e in entries:
        recipe = recipes[e["recipe_id"]]
        ingredient = ingredients[e["ingredient_id"]]
        
        # Get English aliases for this ingredient
        english_aliases = ingredient_aliases.get(ingredient["ingredient_id"], [])
        aliases_text = ", ".join(english_aliases) if english_aliases else ""
        
        rows.append({
            "recipe": recipe["label"],
            "ingredient": ingredient["label"],
            "amount": e.get("amount_raw"),
            "preparation": e.get("preparation"),
            "notes": e.get("notes"),
            "aliases": aliases_text
        })
        
        recipe_counts[recipe["label"]] += 1
        ingredient_counts[ingredient["label"]] += 1
    
    print(f"✅ Created {len(rows)} rows")
    
    # Show statistics
    print(f"\n📈 Statistics:")
    print(f"   • {len(recipe_counts)} unique recipes in output")
    print(f"   • {len(ingredient_counts)} unique ingredients in output")
    
    if recipe_counts:
        max_recipe = recipe_counts.most_common(1)[0]
        print(f"   • Most ingredients in recipe: '{max_recipe[0]}' ({max_recipe[1]} ingredients)")
        
    if ingredient_counts:
        max_ingredient = ingredient_counts.most_common(1)[0]
        print(f"   • Most used ingredient: '{max_ingredient[0]}' ({max_ingredient[1]} times)")
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Write output
    print(f"\n💾 Writing to: {out_path}")
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        
        # Check file size
        file_size = os.path.getsize(out_path)
        if file_size < 100:
            print(f"⚠️  Warning: Output file is very small ({file_size} bytes)")
        else:
            print(f"✅ Wrote {file_size:,} bytes")
            
    except Exception as e:
        print(f"❌ Error writing output file: {e}")
        sys.exit(1)
    
    # Show sample of output
    if rows:
        print(f"\n📄 Sample output (first entry):")
        sample = rows[0]
        for key, value in sample.items():
            display_value = value if value else "(empty)"
            print(f"   • {key}: {display_value}")
    
    print(f"\n🎉 Export complete! Ready for web app.")
    print(f"💡 Test locally: cd docs && python -m http.server 8000")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("❌ Usage: export_long.py data/MASTER.json docs/kyphi_long.json")
        sys.exit(1)
    
    try:
        export(sys.argv[1], sys.argv[2])
    except KeyboardInterrupt:
        print(f"\n⚠️  Export cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)