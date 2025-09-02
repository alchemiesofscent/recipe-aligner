#!/usr/bin/env python3
"""
Ingredient Database Analysis Tool

Usage:
    python scripts/ingredient_db.py --list-slugs      # Get all existing slugs
    python scripts/ingredient_db.py --search myrrh    # Find similar ingredients
    python scripts/ingredient_db.py --stats           # Show database statistics
    python scripts/ingredient_db.py --export-context  # Export for prompt context
"""

import json, sys, argparse
from collections import Counter
from difflib import SequenceMatcher
import re

def load_master():
    with open("data/MASTER.json", "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_for_search(text):
    """Normalize text for fuzzy matching"""
    # Remove diacritics and convert to lowercase
    text = text.lower()
    # Remove common punctuation and spaces
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    return text

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, normalize_for_search(a), normalize_for_search(b)).ratio()

def find_similar_ingredients(master, query, threshold=0.4):
    """Find ingredients similar to query string"""
    ingredients = master.get("ingredients", [])
    aliases = master.get("aliases", [])
    
    # Build lookup of ingredient_id to ingredient
    ingredients_by_id = {i["ingredient_id"]: i for i in ingredients}
    
    matches = []
    
    # Check against ingredient labels
    for ingredient in ingredients:
        sim = similarity(query, ingredient["label"])
        if sim > threshold:
            matches.append({
                "type": "ingredient",
                "slug": ingredient["slug"], 
                "label": ingredient["label"],
                "language": ingredient.get("language", "unknown"),
                "similarity": sim
            })
    
    # Check against aliases
    for alias in aliases:
        sim = similarity(query, alias["variant_label"])
        if sim > threshold:
            ingredient = ingredients_by_id.get(alias["ingredient_id"])
            if ingredient:
                matches.append({
                    "type": "alias",
                    "slug": ingredient["slug"],
                    "label": f"{ingredient['label']} (alias: {alias['variant_label']})",
                    "language": alias.get("language", "unknown"),
                    "similarity": sim
                })
    
    # Sort by similarity, remove duplicates
    seen_slugs = set()
    unique_matches = []
    for match in sorted(matches, key=lambda x: x["similarity"], reverse=True):
        if match["slug"] not in seen_slugs:
            unique_matches.append(match)
            seen_slugs.add(match["slug"])
    
    return unique_matches

def main():
    parser = argparse.ArgumentParser(description="Ingredient Database Tool")
    parser.add_argument("--list-slugs", action="store_true", help="List all ingredient slugs")
    parser.add_argument("--search", type=str, help="Search for similar ingredients")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--export-context", action="store_true", help="Export context for prompts")
    
    args = parser.parse_args()
    
    try:
        master = load_master()
    except FileNotFoundError:
        print("Error: data/MASTER.json not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in MASTER.json: {e}")
        sys.exit(1)
    
    if args.list_slugs:
        print("Existing ingredient slugs:")
        for ingredient in sorted(master.get("ingredients", []), key=lambda x: x["slug"]):
            lang = f" ({ingredient.get('language', 'unknown')})" if ingredient.get("language") else ""
            print(f"  {ingredient['slug']}: {ingredient['label']}{lang}")
    
    elif args.search:
        print(f"Searching for ingredients similar to: '{args.search}'")
        matches = find_similar_ingredients(master, args.search)
        
        if not matches:
            print("No similar ingredients found.")
        else:
            print(f"Found {len(matches)} similar ingredients:")
            for match in matches:
                print(f"  {match['similarity']:.2f} - {match['slug']}: {match['label']} ({match['language']})")
    
    elif args.stats:
        ingredients = master.get("ingredients", [])
        aliases = master.get("aliases", [])
        entries = master.get("entries", [])
        recipes = master.get("recipes", [])
        
        # Language distribution
        ing_langs = Counter(i.get("language", "unknown") for i in ingredients)
        alias_langs = Counter(a.get("language", "unknown") for a in aliases)
        
        print("Database Statistics:")
        print(f"  Recipes: {len(recipes)}")
        print(f"  Ingredients: {len(ingredients)}")
        print(f"  Aliases: {len(aliases)}")
        print(f"  Entries: {len(entries)}")
        
        print(f"\nIngredient Languages:")
        for lang, count in ing_langs.most_common():
            print(f"  {lang}: {count}")
        
        print(f"\nAlias Languages:")
        for lang, count in alias_langs.most_common():
            print(f"  {lang}: {count}")
        
        # Most common ingredients
        ingredient_usage = Counter()
        ingredients_by_id = {i["ingredient_id"]: i for i in ingredients}
        
        for entry in entries:
            ingredient = ingredients_by_id.get(entry["ingredient_id"])
            if ingredient:
                ingredient_usage[ingredient["slug"]] += 1
        
        if ingredient_usage:
            print(f"\nMost Used Ingredients:")
            for slug, count in ingredient_usage.most_common(10):
                ingredient = next((i for i in ingredients if i["slug"] == slug), None)
                if ingredient:
                    print(f"  {slug}: {ingredient['label']} ({count} uses)")
    
    elif args.export_context:
        # Export ingredient slugs in a format suitable for copy-paste into prompts
        slugs = [i["slug"] for i in sorted(master.get("ingredients", []), key=lambda x: x["slug"])]
        
        print("Existing ingredient slugs for prompt context:")
        print("(Copy this list when asked for existing slugs)")
        print("")
        print(", ".join(slugs))
        
        # Also show a structured version
        print(f"\nStructured context ({len(slugs)} ingredients):")
        for ingredient in sorted(master.get("ingredients", []), key=lambda x: x["slug"]):
            lang = f" ({ingredient.get('language', '?')})" if ingredient.get("language") else ""
            print(f"  {ingredient['slug']}: {ingredient['label']}{lang}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()