#!/usr/bin/env python3
"""
Validate recipe completeness - check that all recipes have the expected number of entries.

This script checks MASTER.json for potential data quality issues:
- Recipes with suspiciously few entries compared to their label
- Recipes where ingredient count doesn't match entry count
- Detection of potential missing optional/alternative ingredients

Usage:
    python3 scripts/validate_completeness.py data/MASTER.json
    python3 scripts/validate_completeness.py data/MASTER.json --strict
"""

import sys
import json
import re
from collections import defaultdict


def extract_ingredient_count_from_label(label):
    """
    Extract expected ingredient count from recipe label if specified.

    Examples:
        "Kyphi of 28 Ingredients" → 28
        "Lunar Kyphi (28 ingredients)" → 28
        "Great Kyphi of 36 ingredients" → 36
    """
    patterns = [
        r'(\d+)\s+[Ii]ngredients',
        r'\((\d+)\s+ingredients\)',
        r'of\s+(\d+)\s+[Ii]ngredients',
    ]

    for pattern in patterns:
        match = re.search(pattern, label)
        if match:
            return int(match.group(1))

    return None


def validate_completeness(master_path, strict=False):
    """Validate recipe completeness in MASTER.json"""

    print("🔍 Recipe Completeness Validator")
    print("=" * 60)
    print(f"📂 Loading: {master_path}")
    print()

    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = {r['recipe_id']: r for r in data['recipes']}
    ingredients = {i['ingredient_id']: i for i in data['ingredients']}

    # Count entries per recipe
    entries_by_recipe = defaultdict(list)
    for entry in data['entries']:
        entries_by_recipe[entry['recipe_id']].append(entry)

    print(f"📊 Loaded {len(recipes)} recipes, {len(ingredients)} ingredients, {len(data['entries'])} entries")
    print()

    issues = []
    warnings = []

    for recipe_id, recipe in sorted(recipes.items()):
        label = recipe['label']
        slug = recipe['slug']
        entry_count = len(entries_by_recipe[recipe_id])

        # Extract expected count from label
        expected_count = extract_ingredient_count_from_label(label)

        if expected_count is not None:
            if entry_count != expected_count:
                issue = {
                    'type': 'mismatch',
                    'recipe_id': recipe_id,
                    'slug': slug,
                    'label': label,
                    'expected': expected_count,
                    'actual': entry_count,
                    'difference': entry_count - expected_count
                }
                issues.append(issue)
                print(f"❌ MISMATCH: {label}")
                print(f"   Recipe ID: {recipe_id}")
                print(f"   Slug: {slug}")
                print(f"   Expected: {expected_count} ingredients")
                print(f"   Actual: {entry_count} entries")
                print(f"   Difference: {entry_count - expected_count:+d}")
                print()
        else:
            # No explicit count in label, but check for suspiciously low counts
            if entry_count < 5 and strict:
                warning = {
                    'type': 'suspiciously_low',
                    'recipe_id': recipe_id,
                    'slug': slug,
                    'label': label,
                    'actual': entry_count
                }
                warnings.append(warning)
                print(f"⚠️  WARNING: {label}")
                print(f"   Recipe ID: {recipe_id}")
                print(f"   Slug: {slug}")
                print(f"   Entry count: {entry_count} (seems low)")
                print()

    # Check for recipes with optional/alternative markers in notes
    print("🔍 Checking for optional/alternative ingredient patterns...")
    print()

    optional_count = 0
    alternative_count = 0

    for recipe_id, entries in entries_by_recipe.items():
        recipe = recipes[recipe_id]

        recipe_has_optional = False
        recipe_has_alternative = False

        for entry in entries:
            notes = entry.get('notes', '') or ''

            if 'optional' in notes.lower():
                optional_count += 1
                recipe_has_optional = True

            if 'alternative' in notes.lower():
                alternative_count += 1
                recipe_has_alternative = True

        if recipe_has_optional or recipe_has_alternative:
            print(f"ℹ️  {recipe['label']}")
            if recipe_has_optional:
                print(f"   Contains optional ingredients")
            if recipe_has_alternative:
                print(f"   Contains alternative ingredients")
            print()

    print("=" * 60)
    print("📈 SUMMARY")
    print("=" * 60)

    if issues:
        print(f"❌ Found {len(issues)} recipe(s) with mismatched counts:")
        for issue in issues:
            print(f"   • {issue['slug']}: expected {issue['expected']}, got {issue['actual']} ({issue['difference']:+d})")
        print()
    else:
        print("✅ All recipes with explicit ingredient counts match their entries")
        print()

    if warnings:
        print(f"⚠️  Found {len(warnings)} recipe(s) with suspiciously low counts:")
        for warning in warnings:
            print(f"   • {warning['slug']}: {warning['actual']} entries")
        print()

    print(f"ℹ️  {optional_count} entries marked as optional")
    print(f"ℹ️  {alternative_count} entries marked as alternative")
    print()

    if issues:
        print("💡 Tips for fixing mismatches:")
        print("   1. Check original source text for missing ingredients")
        print("   2. Look for Greek markers: ἐν ἄλλῳ (optional), ἢ (or)")
        print("   3. Review AMENDMENT_PLAN.md for amendment workflow")
        print("   4. Use notes field: 'listed as optional' or 'listed as alternative'")
        print()
        return 1

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate_completeness.py data/MASTER.json [--strict]")
        sys.exit(1)

    master_path = sys.argv[1]
    strict = '--strict' in sys.argv

    exit_code = validate_completeness(master_path, strict=strict)
    sys.exit(exit_code)
