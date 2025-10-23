#!/usr/bin/env python3
"""
Recipe Ingestion Assistant

Provides fuzzy matching, slug validation, and auto-generation to assist
Claude Code in ingesting new recipes.

Usage:
    # Fuzzy match an ingredient name
    python scripts/assist_ingestion.py --fuzzy-match "myrrh"

    # Validate that a slug exists
    python scripts/assist_ingestion.py --validate-slug "smyrne"

    # Suggest a slug for a new ingredient
    python scripts/assist_ingestion.py --suggest-slug "σμύρνη" --lang grc

    # Show which equivalence group contains a slug/term
    python scripts/assist_ingestion.py --equivalence-for "myrrh"

    # Export all context for Claude
    python scripts/assist_ingestion.py --export-all
"""

import json
import sys
import argparse
import re
import unicodedata
from difflib import SequenceMatcher


def load_master():
    """Load MASTER.json"""
    with open("data/MASTER.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_context():
    """Load context_slugs.json"""
    try:
        with open("data/context_slugs.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  context_slugs.json not found, using MASTER.json")
        master = load_master()
        return {
            "recipes": master.get("recipes", []),
            "ingredients": master.get("ingredients", [])
        }


def load_equivalences():
    """Load docs/equivalences.json"""
    try:
        with open("docs/equivalences.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def normalize_greek(text):
    """Remove diacritics from Greek text"""
    # NFD decomposition separates base characters from diacritics
    nfd = unicodedata.normalize('NFD', text)
    # Filter out combining diacritical marks
    return ''.join(c for c in nfd if not unicodedata.combining(c))


def suggest_slug(label, language):
    """Auto-generate slug from label based on language"""
    if language == 'grc':
        # Greek: remove diacritics, transliterate
        cleaned = normalize_greek(label)
        # Simple Greek to Latin transliteration
        trans = str.maketrans({
            'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e',
            'ζ': 'z', 'η': 'e', 'θ': 'th', 'ι': 'i', 'κ': 'k',
            'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o',
            'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't',
            'υ': 'y', 'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
            'ά': 'a', 'έ': 'e', 'ή': 'e', 'ί': 'i', 'ό': 'o',
            'ύ': 'y', 'ώ': 'o'
        })
        slug = cleaned.lower().translate(trans)
        # Clean up
        slug = re.sub(r'[^a-z]+', '-', slug).strip('-')
        return slug

    elif language == 'egy':
        # Egyptian: use as-is but clean for slug format
        slug = label.lower()
        # Remove dots, braces, special chars but keep hyphens
        slug = re.sub(r'[.(){}\[\]]', '', slug)
        slug = re.sub(r'[^a-z0-9\-]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)  # Collapse multiple hyphens
        return slug.strip('-')

    else:
        # Default: kebab-case
        slug = label.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        return slug.strip('-')


def find_equivalence_group(search_term, equivalences):
    """Find which equivalence group contains a term"""
    search_norm = search_term.lower().strip()
    for group_name, terms in equivalences.items():
        for term in terms:
            if term.lower().strip() == search_norm:
                return group_name
    return None


def fuzzy_match(query, top_n=5):
    """Find top N similar ingredients"""
    master = load_master()
    equivalences = load_equivalences()

    ingredients = master.get("ingredients", [])
    aliases = master.get("aliases", [])

    # Build lookups
    ing_by_id = {i["ingredient_id"]: i for i in ingredients}

    matches = []
    query_norm = query.lower().strip()

    # Match against ingredient labels
    for ing in ingredients:
        sim = SequenceMatcher(None, query_norm, ing["label"].lower()).ratio()
        if sim > 0.3:
            eq_group = find_equivalence_group(ing["slug"], equivalences)
            matches.append({
                'slug': ing['slug'],
                'label': ing['label'],
                'language': ing.get('language', '?'),
                'similarity': sim,
                'equivalence_group': eq_group,
                'match_type': 'label'
            })

    # Match against aliases
    for alias in aliases:
        sim = SequenceMatcher(None, query_norm, alias["variant_label"].lower()).ratio()
        if sim > 0.3:
            ing = ing_by_id.get(alias["ingredient_id"])
            if ing:
                eq_group = find_equivalence_group(ing["slug"], equivalences)
                matches.append({
                    'slug': ing['slug'],
                    'label': f"{ing['label']} (via alias: {alias['variant_label']})",
                    'language': alias.get('language', '?'),
                    'similarity': sim,
                    'equivalence_group': eq_group,
                    'match_type': 'alias'
                })

    # Sort by similarity, dedupe by slug
    seen = set()
    unique = []
    for m in sorted(matches, key=lambda x: x['similarity'], reverse=True):
        if m['slug'] not in seen:
            unique.append(m)
            seen.add(m['slug'])

    return unique[:top_n]


def validate_slug(slug):
    """Check if a slug exists in the database"""
    context = load_context()
    ingredients = context.get("ingredients", [])

    for ing in ingredients:
        if ing["slug"] == slug:
            return True, ing
    return False, None


def equivalence_for(term):
    """Show which equivalence group contains a term"""
    equivalences = load_equivalences()
    group_name = find_equivalence_group(term, equivalences)

    if group_name:
        return group_name, equivalences[group_name]
    return None, None


def export_all():
    """Export all context for Claude Code"""
    context = load_context()
    equivalences = load_equivalences()

    print("=" * 60)
    print("RECIPE ALIGNER CONTEXT (for Claude Code)")
    print("=" * 60)
    print()

    print("📊 STATISTICS:")
    print(f"  • {len(context.get('recipes', []))} recipes")
    print(f"  • {len(context.get('ingredients', []))} ingredients")
    print(f"  • {len(equivalences)} equivalence groups")
    print()

    print("🌿 EXISTING INGREDIENT SLUGS:")
    print()
    for ing in sorted(context.get("ingredients", []), key=lambda x: x["slug"]):
        lang_tag = f" ({ing.get('language', '?')})" if ing.get("language") else ""
        print(f"  {ing['slug']}: {ing['label']}{lang_tag}")

    print()
    print("=" * 60)
    print("🔗 EQUIVALENCE GROUPS:")
    print("=" * 60)
    print()

    for group_name, terms in sorted(equivalences.items()):
        print(f"{group_name}:")
        print(f"  {', '.join(terms)}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Recipe Ingestion Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find similar ingredients
  python scripts/assist_ingestion.py --fuzzy-match "myrrh"

  # Check if slug exists
  python scripts/assist_ingestion.py --validate-slug "smyrne"

  # Generate slug suggestion
  python scripts/assist_ingestion.py --suggest-slug "σμύρνη" --lang grc

  # Find equivalence group
  python scripts/assist_ingestion.py --equivalence-for "myrrh"

  # Export all context
  python scripts/assist_ingestion.py --export-all
        """
    )

    parser.add_argument("--fuzzy-match", type=str, metavar="QUERY",
                       help="Find similar ingredients using fuzzy matching")
    parser.add_argument("--validate-slug", type=str, metavar="SLUG",
                       help="Check if a slug exists")
    parser.add_argument("--suggest-slug", type=str, metavar="LABEL",
                       help="Suggest a slug for a new ingredient")
    parser.add_argument("--lang", type=str, metavar="CODE",
                       help="Language code for slug suggestion (grc, egy, en, la)")
    parser.add_argument("--equivalence-for", type=str, metavar="TERM",
                       help="Show which equivalence group contains a term")
    parser.add_argument("--export-all", action="store_true",
                       help="Export all context for Claude Code")

    args = parser.parse_args()

    try:
        if args.fuzzy_match:
            print(f"🔍 Fuzzy matching: '{args.fuzzy_match}'")
            print()
            matches = fuzzy_match(args.fuzzy_match)

            if not matches:
                print("❌ No similar ingredients found")
                return

            print(f"Found {len(matches)} similar ingredients:")
            print()

            for i, match in enumerate(matches, 1):
                eq_info = f" [in group: {match['equivalence_group']}]" if match['equivalence_group'] else ""
                sim_pct = int(match['similarity'] * 100)
                print(f"  [{i}] {match['slug']}")
                print(f"      Label: {match['label']}")
                print(f"      Language: {match['language']}")
                print(f"      Similarity: {sim_pct}%{eq_info}")
                print()

        elif args.validate_slug:
            exists, ing = validate_slug(args.validate_slug)
            if exists:
                print(f"✅ Slug exists: {args.validate_slug}")
                print(f"   Label: {ing['label']}")
                print(f"   Language: {ing.get('language', '?')}")
            else:
                print(f"❌ Slug not found: {args.validate_slug}")
                sys.exit(1)

        elif args.suggest_slug:
            if not args.lang:
                print("❌ --lang required for slug suggestion")
                parser.print_help()
                sys.exit(1)

            suggested = suggest_slug(args.suggest_slug, args.lang)
            print(f"💡 Suggested slug: {suggested}")
            print(f"   From: {args.suggest_slug} ({args.lang})")

            # Check if it already exists
            exists, _ = validate_slug(suggested)
            if exists:
                print(f"   ⚠️  Warning: This slug already exists!")

        elif args.equivalence_for:
            group_name, terms = equivalence_for(args.equivalence_for)
            if group_name:
                print(f"✅ Found in equivalence group: '{group_name}'")
                print()
                print(f"All terms in '{group_name}':")
                for term in terms:
                    print(f"  • {term}")
            else:
                print(f"❌ '{args.equivalence_for}' not found in any equivalence group")

        elif args.export_all:
            export_all()

        else:
            parser.print_help()

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
