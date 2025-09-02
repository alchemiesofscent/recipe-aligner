#!/usr/bin/env python3
"""
Merge a diff.json (GPT output) into the canonical data/MASTER.json.

Usage:
    python scripts/merge_diff.py data/MASTER.json diffs/my_diff.json [added_by]

- Assigns new IDs for recipes, ingredients, aliases, and entries.
- Deduplicates existing recipes/ingredients by slug.
- Deduplicates aliases by (ingredient_id + variant_label).
- Deduplicates entries by (recipe_id, ingredient_id, amount_raw, preparation).
- Stamps new entries with added_at + added_by.
"""

import json, sys, datetime

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def idx_by(arr, key):
    return {x[key]: x for x in arr}

def next_id(arr, key):
    return (max([x.get(key,0) for x in arr]) + 1) if arr else 1

def merge(master_path, diff_path, added_by="gpt"):
    print(f"📁 Loading master: {master_path}")
    master = load(master_path)
    
    print(f"📄 Loading diff: {diff_path}")
    diff = load(diff_path)
    
    print(f"👤 Added by: {added_by}")
    print()
    
    # Show current state
    print(f"📊 Current master contains:")
    print(f"   • {len(master.get('recipes', []))} recipes")
    print(f"   • {len(master.get('ingredients', []))} ingredients") 
    print(f"   • {len(master.get('aliases', []))} aliases")
    print(f"   • {len(master.get('entries', []))} entries")
    print()
    
    # Show diff contents
    print(f"📦 Diff contains:")
    print(f"   • {len(diff.get('recipes', []))} recipes")
    print(f"   • {len(diff.get('ingredients', []))} ingredients")
    print(f"   • {len(diff.get('aliases', []))} aliases") 
    print(f"   • {len(diff.get('entries', []))} entries")
    print()

    recipes_by_slug = idx_by(master["recipes"], "slug")
    ingredients_by_slug = idx_by(master["ingredients"], "slug")

    # Counters for summary
    added_recipes = 0
    added_ingredients = 0 
    added_aliases = 0
    added_entries = 0
    skipped_recipes = 0
    skipped_ingredients = 0
    skipped_aliases = 0
    skipped_entries = 0

    # 1) Process Recipes
    print("🍯 Processing recipes...")
    for r in diff.get("recipes", []):
        if r["slug"] not in recipes_by_slug:
            new_id = next_id(master["recipes"], "recipe_id")
            new = {"recipe_id": new_id, **r}
            master["recipes"].append(new)
            recipes_by_slug[new["slug"]] = new
            added_recipes += 1
            print(f"   ✅ Added recipe: '{r['label']}' (ID {new_id})")
        else:
            existing = recipes_by_slug[r["slug"]]
            skipped_recipes += 1
            print(f"   ⏭️  Skipped existing recipe: '{r['slug']}' (ID {existing['recipe_id']})")

    # 2) Process Ingredients
    print(f"\n🌿 Processing ingredients...")
    for ing in diff.get("ingredients", []):
        slug = ing["slug"]
        if slug in ingredients_by_slug:
            existing = ingredients_by_slug[slug]
            # Warn if label differs
            if existing["label"] != ing["label"]:
                print(f"   ⚠️  Label collision for '{slug}': "
                      f"existing='{existing['label']}' vs new='{ing['label']}'")
            skipped_ingredients += 1
            print(f"   ⏭️  Skipped existing ingredient: '{slug}' (ID {existing['ingredient_id']})")
            continue
        
        new_id = next_id(master["ingredients"], "ingredient_id")
        new = {"ingredient_id": new_id, **ing}
        master["ingredients"].append(new)
        ingredients_by_slug[new["slug"]] = new
        added_ingredients += 1
        print(f"   ✅ Added ingredient: '{ing['label']}' (ID {new_id})")

    # 3) Process Aliases
    print(f"\n🏷️  Processing aliases...")
    seen_alias = {(a["ingredient_id"], a["variant_label"]) for a in master.get("aliases", [])}
    for a in diff.get("aliases", []):
        ing = ingredients_by_slug.get(a["ingredient_slug"])
        if not ing:
            print(f"   ❌ Skipping alias - unknown ingredient_slug: '{a['ingredient_slug']}'")
            continue
        
        key = (ing["ingredient_id"], a["variant_label"])
        if key in seen_alias:
            skipped_aliases += 1
            print(f"   ⏭️  Skipped existing alias: '{ing['slug']}' → '{a['variant_label']}'")
            continue
            
        new_id = next_id(master["aliases"], "alias_id")
        master["aliases"].append({
            "alias_id": new_id,
            "ingredient_id": ing["ingredient_id"],
            "variant_label": a["variant_label"],
            "language": a.get("language"),
            "source": a.get("source")
        })
        seen_alias.add(key)
        added_aliases += 1
        print(f"   ✅ Added alias: '{ing['slug']}' → '{a['variant_label']}' (ID {new_id})")

    # 4) Process Entries
    print(f"\n📝 Processing entries...")
    seen_entry = {
        (e["recipe_id"], e["ingredient_id"], e.get("amount_raw",""), e.get("preparation","") or "")
        for e in master.get("entries", [])
    }
    
    for e in diff.get("entries", []):
        r = recipes_by_slug.get(e["recipe_slug"])
        i = ingredients_by_slug.get(e["ingredient_slug"])
        
        if not r:
            print(f"   ❌ Skipping entry - unknown recipe_slug: '{e['recipe_slug']}'")
            continue
        if not i:
            print(f"   ❌ Skipping entry - unknown ingredient_slug: '{e['ingredient_slug']}'")
            continue
            
        tup = (r["recipe_id"], i["ingredient_id"], e.get("amount_raw",""), e.get("preparation","") or "")
        if tup in seen_entry:
            skipped_entries += 1
            print(f"   ⏭️  Skipped duplicate: '{r['slug']}' + '{i['slug']}'")
            continue
            
        new_id = next_id(master["entries"], "entry_id")
        timestamp = datetime.datetime.utcnow().isoformat()
        
        master["entries"].append({
            "entry_id": new_id,
            "recipe_id": r["recipe_id"],
            "ingredient_id": i["ingredient_id"],
            "amount_raw": e.get("amount_raw"),
            "amount_value": e.get("amount_value"),
            "amount_unit": e.get("amount_unit"),
            "preparation": e.get("preparation"),
            "notes": e.get("notes"),
            "source_citation": e.get("source_citation"),
            "source_span": e.get("source_span"),
            "added_at": timestamp,
            "added_by": added_by
        })
        seen_entry.add(tup)
        added_entries += 1
        
        # Show entry details
        amount_info = f" ({e.get('amount_raw', 'no amount')})" if e.get("amount_raw") else ""
        prep_info = f" [{e.get('preparation')}]" if e.get("preparation") else ""
        print(f"   ✅ Added entry: '{r['slug']}' + '{i['slug']}'{amount_info}{prep_info} (ID {new_id})")

    # Save the updated master
    print(f"\n💾 Saving updated master to {master_path}")
    save(master_path, master)

    # Summary
    print(f"\n✅ Merge complete!")
    print(f"   📊 Added: {added_recipes} recipes, {added_ingredients} ingredients, {added_aliases} aliases, {added_entries} entries")
    if skipped_recipes + skipped_ingredients + skipped_aliases + skipped_entries > 0:
        print(f"   ⏭️  Skipped: {skipped_recipes} recipes, {skipped_ingredients} ingredients, {skipped_aliases} aliases, {skipped_entries} entries")
    
    print(f"\n📈 New totals:")
    print(f"   • {len(master['recipes'])} recipes")
    print(f"   • {len(master['ingredients'])} ingredients")
    print(f"   • {len(master['aliases'])} aliases")
    print(f"   • {len(master['entries'])} entries")
    
    if added_entries > 0:
        print(f"\n💡 Next step: python scripts/export_long.py {master_path} docs/kyphi_long.json")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("❌ Usage: merge_diff.py data/MASTER.json diffs/your_diff.json [added_by]")
        sys.exit(1)
    
    print("🔄 Kyphi Merge Diff")
    print("=" * 50)
    
    try:
        merge(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else "gpt")
        print("\n🎉 Success! Diff merged successfully.")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)