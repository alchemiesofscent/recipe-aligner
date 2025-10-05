#!/usr/bin/env python3
"""
Simple Ingredient Linking Tool (improved)

Usage:
    python scripts/link_ingredients.py diffs/my_diff.json

Now uses:
- English aliases from MASTER
- Curated equivalences (docs/equivalences.json)
- Light lemmatization (Greek/Latin) with overrides

to suggest higher-quality cross-language matches.
"""

import json, sys, os
from difflib import SequenceMatcher
import re
import unicodedata
from typing import Dict, List, Any

# Keep the tool simple: no external lemma/override files.

def normalize(text):
    """Simple normalization for matching"""
    if text is None:
        return ""
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    return re.sub(r'[^\w\s]', '', text)


def load_equivalences(path: str = os.path.join('docs', 'equivalences.json')) -> Dict[str, List[str]]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            eq = json.load(f)
        # Normalize all variants for quick lookup
        return {k: [normalize(v) for v in (eq.get(k) or [])] for k in eq.keys()}
    except FileNotFoundError:
        return {}


def load_synonyms(path: str = None) -> Dict[str, List[str]]:
    # Deprecated; synonyms are handled via docs/equivalences.json variants
    return {}

def build_indices(master: dict, equivalences: Dict[str, List[str]]):
    """Build quick lookup indices for labels, aliases, and equivalence variants."""
    ingredients = master.get('ingredients', [])
    aliases = master.get('aliases', [])

    # Ingredient indices
    by_label: Dict[str, List[dict]] = {}
    # by_label_lemma not used (no external lemma at this stage)
    for ing in ingredients:
        key = normalize(ing.get('label'))
        by_label.setdefault(key, []).append(ing)

    # Alias index (any language)
    alias_to_ing: Dict[str, List[dict]] = {}
    # alias_lemma_to_ing not used
    for a in aliases:
        ing = next((i for i in ingredients if i.get('ingredient_id') == a.get('ingredient_id')), None)
        if not ing:
            continue
        key = normalize(a.get('variant_label'))
        alias_to_ing.setdefault(key, []).append(ing)

    # Equivalence map variant->list of variants in the same group
    variant_group: Dict[str, List[str]] = {}
    for variants in equivalences.values():
        for v in variants:
            variant_group[v] = variants

    return by_label, alias_to_ing, variant_group

def load_existing_ingredients():
    """Load existing ingredients from master"""
    try:
        with open("data/MASTER.json", "r", encoding="utf-8") as f:
            master = json.load(f)
        return master.get("ingredients", [])
    except FileNotFoundError:
        return []

def find_similar(new_label: str, existing_ingredients: List[dict], master: dict,
                 equivalences: Dict[str, List[str]], threshold=0.6):
    """Find similar existing ingredients using aliases + equivalences + fuzzy fallback."""
    new_norm = normalize(new_label)
    by_label, alias_to_ing, variant_group = build_indices(master, equivalences)

    seen = set()
    matches = []

    def push(ing: dict, score: float, why: str):
        key = ing.get('slug')
        if key in seen:
            return
        seen.add(key)
        matches.append({
            'slug': ing.get('slug'),
            'label': ing.get('label'),
            'similarity': score,
            'why': why
        })

    # 0) Prepare candidate terms set (synonyms + lemma)
    cand_terms = {new_norm}

    # 1) Exact alias/label or lemma match
    for term in cand_terms:
        for lst in (
            by_label.get(term, []),
            alias_to_ing.get(term, []),
        ):
            for ing in lst:
                push(ing, 1.0, 'exact-alias/label')
        for ing in lst:
            push(ing, 1.0, 'exact-alias/label')

    # 2) Equivalences group match
    variants = []
    for term in cand_terms:
        if term in variant_group:
            variants = variant_group[term]
            break
    else:
        variants = []
    if variants:
        for v in variants:
            for ing in by_label.get(v, []):
                push(ing, 0.96, 'equivalence-label')
            for ing in alias_to_ing.get(v, []):
                push(ing, 0.95, 'equivalence-alias')

    # 3) Fuzzy fallback over labels only (avoid alias noise)
    if len(matches) == 0:
        for existing in existing_ingredients:
            existing_norm = normalize(existing.get('label'))
            similarity = SequenceMatcher(None, new_norm, existing_norm).ratio()
            if similarity > threshold:
                push(existing, similarity, 'fuzzy')

    # Sort and cap
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches[:10]

def process_diff(diff_path):
    """Process a diff file interactively"""
    print(f"Processing: {diff_path}")
    
    # Load diff
    with open(diff_path, "r", encoding="utf-8") as f:
        diff = json.load(f)
    
    # Load existing ingredients
    try:
        with open("data/MASTER.json", "r", encoding="utf-8") as f:
            master = json.load(f)
    except FileNotFoundError:
        print("Error: data/MASTER.json not found")
        sys.exit(1)
    existing_ingredients = master.get("ingredients", [])
    print(f"Found {len(existing_ingredients)} existing ingredients to match against")

    # Load equivalences
    equivalences = load_equivalences()
    
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
        matches = find_similar(ingredient.get("label"), existing_ingredients, master, equivalences)
        
        if not matches:
            print("No similar ingredients found - keeping as new")
            continue
        
        print("Similar existing ingredients:")
        for i, match in enumerate(matches[:5]):  # Show top 5
            reason = match.get('why', 'match')
            print(f"  {i+1}. {match['slug']}: {match['label']} ({match['similarity']:.2f}, {reason})")
        
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
