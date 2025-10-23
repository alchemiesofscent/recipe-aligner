#!/usr/bin/env python3
"""
Equivalence Management Tool

Manages the semantic groupings of ingredients across languages in docs/equivalences.json

Usage:
    # Suggest updates based on a new diff file
    python scripts/update_equivalences.py --suggest-for-diff diffs/new-recipe.json

    # Interactive mode: manually build/update groups
    python scripts/update_equivalences.py --interactive

    # Validate current equivalences
    python scripts/update_equivalences.py --validate

    # Export for Claude Code context
    python scripts/update_equivalences.py --export-context
"""

import json
import sys
import argparse
from collections import defaultdict
from difflib import SequenceMatcher


def load_master():
    """Load MASTER.json"""
    with open("data/MASTER.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_equivalences():
    """Load docs/equivalences.json"""
    try:
        with open("docs/equivalences.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️  docs/equivalences.json not found, starting fresh")
        return {}


def save_equivalences(equivalences):
    """Save to docs/equivalences.json"""
    with open("docs/equivalences.json", "w", encoding="utf-8") as f:
        json.dump(equivalences, f, ensure_ascii=False, indent=2)
    print("✅ Saved to docs/equivalences.json")


def normalize_text(text):
    """Normalize text for similarity matching"""
    return text.lower().strip()


def find_equivalence_group(search_term, equivalences):
    """Find which equivalence group contains a term (slug, label, or alias)"""
    search_norm = normalize_text(search_term)
    for group_name, terms in equivalences.items():
        for term in terms:
            if normalize_text(term) == search_norm:
                return group_name
    return None


def suggest_for_diff(diff_path):
    """Analyze a diff file and suggest equivalence updates"""
    print(f"📋 Analyzing diff: {diff_path}\n")

    try:
        with open(diff_path, "r", encoding="utf-8") as f:
            diff = json.load(f)
    except Exception as e:
        print(f"❌ Error loading diff: {e}")
        return

    master = load_master()
    equivalences = load_equivalences()

    # Build lookups
    ingredients_by_slug = {i["slug"]: i for i in master.get("ingredients", [])}

    # Collect all terms from the diff (slugs, labels, aliases)
    diff_terms = {}  # slug -> [terms]

    # Add ingredients from diff
    for ing in diff.get("ingredients", []):
        slug = ing["slug"]
        if slug not in diff_terms:
            diff_terms[slug] = set()
        diff_terms[slug].add(ing["label"])
        diff_terms[slug].add(slug)

    # Add aliases from diff
    for alias in diff.get("aliases", []):
        slug = alias["ingredient_slug"]
        if slug not in diff_terms:
            diff_terms[slug] = set()
        diff_terms[slug].add(alias["variant_label"])

        # Also add the ingredient label if it exists
        if slug in ingredients_by_slug:
            diff_terms[slug].add(ingredients_by_slug[slug]["label"])

    if not diff_terms:
        print("ℹ️  No new ingredients or aliases to analyze")
        return

    print("🔍 Found ingredients with aliases:\n")
    suggestions = []

    for slug, terms in diff_terms.items():
        print(f"   {slug}:")
        for term in terms:
            print(f"      • {term}")

        # Check if any terms are already in equivalence groups
        existing_groups = set()
        for term in terms:
            group = find_equivalence_group(term, equivalences)
            if group:
                existing_groups.add(group)

        if existing_groups:
            print(f"   → Found in existing groups: {', '.join(existing_groups)}")
            for group in existing_groups:
                suggestions.append({
                    "slug": slug,
                    "terms": list(terms),
                    "action": "add_to_existing",
                    "group": group
                })
        else:
            # Check for similar groups using fuzzy matching
            similar_groups = []
            for term in terms:
                for group_name, group_terms in equivalences.items():
                    for group_term in group_terms:
                        sim = SequenceMatcher(None,
                                            normalize_text(term),
                                            normalize_text(group_term)).ratio()
                        if sim > 0.6:
                            similar_groups.append((group_name, sim))
                            break

            if similar_groups:
                # Get best match
                best_group = max(similar_groups, key=lambda x: x[1])
                print(f"   → Similar to group: {best_group[0]} (similarity: {best_group[1]:.2f})")
                suggestions.append({
                    "slug": slug,
                    "terms": list(terms),
                    "action": "maybe_add",
                    "group": best_group[0],
                    "similarity": best_group[1]
                })
            else:
                print(f"   → No existing group found")
                suggestions.append({
                    "slug": slug,
                    "terms": list(terms),
                    "action": "create_new",
                    "group": None
                })
        print()

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUGGESTIONS:\n")

    for sugg in suggestions:
        if sugg["action"] == "add_to_existing":
            print(f"✅ ADD to '{sugg['group']}':")
            print(f"   Slug: {sugg['slug']}")
            print(f"   Terms: {', '.join(sugg['terms'])}")
        elif sugg["action"] == "maybe_add":
            print(f"🤔 CONSIDER adding to '{sugg['group']}' (similarity: {sugg['similarity']:.2f}):")
            print(f"   Slug: {sugg['slug']}")
            print(f"   Terms: {', '.join(sugg['terms'])}")
        elif sugg["action"] == "create_new":
            print(f"🆕 CREATE NEW group:")
            print(f"   Slug: {sugg['slug']}")
            print(f"   Terms: {', '.join(sugg['terms'])}")
        print()


def validate():
    """Validate equivalences against MASTER.json"""
    print("🔍 Validating docs/equivalences.json\n")

    master = load_master()
    equivalences = load_equivalences()

    if not equivalences:
        print("❌ No equivalences found")
        return False

    # Build lookup of all valid terms (slugs, labels, aliases)
    valid_terms = set()

    # Add all ingredient slugs and labels
    for ing in master.get("ingredients", []):
        valid_terms.add(ing["slug"])
        valid_terms.add(ing["label"])

    # Add all alias variant labels
    for alias in master.get("aliases", []):
        valid_terms.add(alias["variant_label"])

    errors = []
    warnings = []

    print(f"📊 Checking {len(equivalences)} equivalence groups...\n")

    for group_name, terms in equivalences.items():
        print(f"   {group_name}: {len(terms)} terms")

        # Check each term
        for term in terms:
            if term not in valid_terms:
                errors.append(f"'{group_name}' contains unknown term: '{term}'")

    print()

    if errors:
        print("❌ ERRORS FOUND:\n")
        for err in errors:
            print(f"   • {err}")
        return False
    else:
        print("✅ All equivalences are valid!")
        return True


def export_context():
    """Export equivalences in a format suitable for Claude Code context"""
    equivalences = load_equivalences()

    if not equivalences:
        print("No equivalences found")
        return

    print("=" * 60)
    print("EQUIVALENCE GROUPS (for Claude Code context)")
    print("=" * 60)
    print()

    for group_name, terms in sorted(equivalences.items()):
        print(f"{group_name}:")
        print(f"  Terms: {', '.join(terms)}")
        print()


def interactive():
    """Interactive mode for building equivalence groups"""
    print("🎨 Interactive Equivalence Builder")
    print("=" * 60)
    print()
    print("This mode helps you manually create and update equivalence groups.")
    print("You'll be prompted to group ingredients that represent the same substance.")
    print()

    master = load_master()
    equivalences = load_equivalences()

    print(f"Current state:")
    print(f"  • {len(master.get('ingredients', []))} ingredients in MASTER.json")
    print(f"  • {len(equivalences)} existing equivalence groups")
    print()

    while True:
        print("\nOptions:")
        print("  [1] Add terms to existing group")
        print("  [2] Create new equivalence group")
        print("  [3] View all groups")
        print("  [4] Save and exit")
        print("  [q] Quit without saving")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "1":
            # Add to existing
            print("\nExisting groups:")
            groups = list(equivalences.keys())
            for i, group in enumerate(groups, 1):
                print(f"  [{i}] {group}")

            group_choice = input("\nEnter group number: ").strip()
            try:
                group_idx = int(group_choice) - 1
                group_name = groups[group_idx]

                print(f"\nCurrent terms in '{group_name}':")
                print(f"  {', '.join(equivalences[group_name])}")

                new_terms = input("\nEnter terms to add (comma-separated): ").strip()
                if new_terms:
                    terms = [t.strip() for t in new_terms.split(",") if t.strip()]
                    equivalences[group_name].extend(terms)
                    # Remove duplicates
                    equivalences[group_name] = list(set(equivalences[group_name]))
                    print(f"✅ Added {len(terms)} terms to '{group_name}'")
            except (ValueError, IndexError):
                print("❌ Invalid selection")

        elif choice == "2":
            # Create new group
            group_name = input("\nNew group name: ").strip()
            if not group_name:
                print("❌ Group name required")
                continue

            if group_name in equivalences:
                print(f"❌ Group '{group_name}' already exists")
                continue

            terms = input("Enter terms (comma-separated): ").strip()
            if terms:
                term_list = [t.strip() for t in terms.split(",") if t.strip()]
                equivalences[group_name] = term_list
                print(f"✅ Created group '{group_name}' with {len(term_list)} terms")

        elif choice == "3":
            # View all
            print("\n" + "=" * 60)
            for group_name, terms in sorted(equivalences.items()):
                print(f"\n{group_name}:")
                for term in terms:
                    print(f"  • {term}")
            print("=" * 60)

        elif choice == "4":
            # Save and exit
            save_equivalences(equivalences)
            print("👋 Saved and exiting")
            break

        elif choice == "q":
            # Quit without saving
            confirm = input("Quit without saving? (y/n): ").strip().lower()
            if confirm == "y":
                print("👋 Exiting without saving")
                break


def main():
    parser = argparse.ArgumentParser(
        description="Equivalence Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a diff and suggest equivalence updates
  python scripts/update_equivalences.py --suggest-for-diff diffs/new-recipe.json

  # Interactive mode
  python scripts/update_equivalences.py --interactive

  # Validate
  python scripts/update_equivalences.py --validate

  # Export context for Claude
  python scripts/update_equivalences.py --export-context
        """
    )

    parser.add_argument("--suggest-for-diff", type=str, metavar="PATH",
                       help="Analyze a diff file and suggest equivalence updates")
    parser.add_argument("--interactive", action="store_true",
                       help="Interactive mode for manually building groups")
    parser.add_argument("--validate", action="store_true",
                       help="Validate current equivalences against MASTER.json")
    parser.add_argument("--export-context", action="store_true",
                       help="Export equivalences for Claude Code context")

    args = parser.parse_args()

    if args.suggest_for_diff:
        suggest_for_diff(args.suggest_for_diff)
    elif args.interactive:
        interactive()
    elif args.validate:
        success = validate()
        sys.exit(0 if success else 1)
    elif args.export_context:
        export_context()
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
