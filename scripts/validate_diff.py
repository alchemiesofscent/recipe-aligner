#!/usr/bin/env python3
"""
Validate diff files locally before committing.

Usage:
    python scripts/validate_diff.py diffs/my_diff.json
    python scripts/validate_diff.py diffs/*.json  (validate all)

Checks:
- JSON schema compliance  
- Data consistency (slugs, references)
- Common mistakes (empty fields, duplicates within diff)
- Provides suggestions for improvements
"""

import json, sys, glob, os
from collections import Counter, defaultdict

def load_schema():
    schema_path = "data/schema_diff.json"
    if not os.path.exists(schema_path):
        print(f"❌ Schema not found: {schema_path}")
        return None
    
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_json_schema(data, schema):
    """Basic JSON schema validation without jsonschema library"""
    errors = []
    
    # Check required top-level fields
    required = schema.get("required", [])
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Check data types and required fields in arrays
    for section in ["recipes", "ingredients", "aliases", "entries"]:
        if section not in data:
            continue
            
        items = data[section]
        if not isinstance(items, list):
            errors.append(f"{section} must be an array")
            continue
            
        section_schema = schema["properties"][section]["items"]
        required_fields = section_schema.get("required", [])
        
        for i, item in enumerate(items):
            for req_field in required_fields:
                if req_field not in item:
                    errors.append(f"{section}[{i}] missing required field: {req_field}")
    
    return errors

def validate_diff(diff_path):
    print(f"🔍 Validating: {diff_path}")
    print("-" * 60)
    
    # Load and parse JSON
    try:
        with open(diff_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Load schema
    schema = load_schema()
    if not schema:
        return False
    
    errors = []
    warnings = []
    suggestions = []
    
    # 1. Schema validation
    print("📋 Checking JSON schema...")
    schema_errors = validate_json_schema(data, schema)
    if schema_errors:
        errors.extend(schema_errors)
        for err in schema_errors:
            print(f"   ❌ {err}")
    else:
        print("   ✅ Schema valid")
    
    # 2. Content validation
    recipes = data.get("recipes", [])
    ingredients = data.get("ingredients", [])
    aliases = data.get("aliases", [])
    entries = data.get("entries", [])
    
    print(f"\n📊 Content summary:")
    print(f"   • {len(recipes)} recipes")
    print(f"   • {len(ingredients)} ingredients")
    print(f"   • {len(aliases)} aliases")
    print(f"   • {len(entries)} entries")
    
    # 3. Check for duplicates within diff
    print(f"\n🔍 Checking for internal duplicates...")
    
    recipe_slugs = [r["slug"] for r in recipes]
    recipe_dupes = [slug for slug, count in Counter(recipe_slugs).items() if count > 1]
    if recipe_dupes:
        errors.append(f"Duplicate recipe slugs: {recipe_dupes}")
        print(f"   ❌ Duplicate recipe slugs: {recipe_dupes}")
    
    ingredient_slugs = [i["slug"] for i in ingredients]
    ingredient_dupes = [slug for slug, count in Counter(ingredient_slugs).items() if count > 1]
    if ingredient_dupes:
        errors.append(f"Duplicate ingredient slugs: {ingredient_dupes}")
        print(f"   ❌ Duplicate ingredient slugs: {ingredient_dupes}")
    
    if not recipe_dupes and not ingredient_dupes:
        print("   ✅ No internal duplicates")
    
    # 4. Check references
    print(f"\n🔗 Checking references...")
    
    recipe_slug_set = set(recipe_slugs)
    ingredient_slug_set = set(ingredient_slugs)
    
    # Check alias references
    bad_alias_refs = []
    for alias in aliases:
        if alias["ingredient_slug"] not in ingredient_slug_set:
            bad_alias_refs.append(alias["ingredient_slug"])
    
    if bad_alias_refs:
        errors.append(f"Aliases reference unknown ingredients: {set(bad_alias_refs)}")
        print(f"   ❌ Aliases reference unknown ingredients: {set(bad_alias_refs)}")
    
    # Check entry references  
    bad_entry_recipe_refs = []
    bad_entry_ingredient_refs = []
    
    for entry in entries:
        if entry["recipe_slug"] not in recipe_slug_set:
            bad_entry_recipe_refs.append(entry["recipe_slug"])
        if entry["ingredient_slug"] not in ingredient_slug_set:
            bad_entry_ingredient_refs.append(entry["ingredient_slug"])
    
    if bad_entry_recipe_refs:
        errors.append(f"Entries reference unknown recipes: {set(bad_entry_recipe_refs)}")
        print(f"   ❌ Entries reference unknown recipes: {set(bad_entry_recipe_refs)}")
        
    if bad_entry_ingredient_refs:
        errors.append(f"Entries reference unknown ingredients: {set(bad_entry_ingredient_refs)}")
        print(f"   ❌ Entries reference unknown ingredients: {set(bad_entry_ingredient_refs)}")
    
    if not bad_alias_refs and not bad_entry_recipe_refs and not bad_entry_ingredient_refs:
        print("   ✅ All references valid")
    
    # 5. Data quality checks
    print(f"\n🧐 Data quality checks...")
    
    # Check for empty/placeholder values
    empty_amounts = sum(1 for e in entries if e.get("amount_raw") in [None, "", "—", "?"])
    if empty_amounts > 0:
        warnings.append(f"{empty_amounts} entries have empty/placeholder amounts")
        print(f"   ⚠️  {empty_amounts} entries have empty/placeholder amounts")
    
    # Check for very short labels
    short_labels = []
    for recipe in recipes:
        if len(recipe["label"]) < 3:
            short_labels.append(f"recipe '{recipe['slug']}'")
    for ingredient in ingredients:
        if len(ingredient["label"]) < 2:
            short_labels.append(f"ingredient '{ingredient['slug']}'")
            
    if short_labels:
        warnings.append(f"Very short labels: {short_labels}")
        print(f"   ⚠️  Very short labels: {short_labels}")
    
    # Check for missing language tags on non-English content
    non_ascii_without_lang = []
    for ingredient in ingredients:
        label = ingredient["label"]
        if any(ord(c) > 127 for c in label) and not ingredient.get("language"):
            non_ascii_without_lang.append(ingredient["slug"])
    
    if non_ascii_without_lang:
        suggestions.append(f"Consider adding language tags for: {non_ascii_without_lang}")
        print(f"   💡 Consider adding language tags for: {non_ascii_without_lang}")
    
    if not warnings and not suggestions:
        print("   ✅ Data quality looks good")
    
    # 6. Suggestions
    if suggestions:
        print(f"\n💡 Suggestions:")
        for suggestion in suggestions:
            print(f"   • {suggestion}")
    
    # Summary
    print(f"\n{'='*60}")
    if errors:
        print(f"❌ Validation failed with {len(errors)} errors:")
        for error in errors:
            print(f"   • {error}")
        return False
    elif warnings:
        print(f"⚠️  Validation passed with {len(warnings)} warnings - ready to commit")
        return True
    else:
        print(f"✅ Validation passed - excellent quality!")
        return True

def main():
    if len(sys.argv) < 2:
        print("❌ Usage: validate_diff.py diffs/your_diff.json")
        print("   Or: validate_diff.py diffs/*.json")
        sys.exit(1)
    
    print("🔄 Kyphi Diff Validator")
    print("=" * 60)
    
    # Handle glob patterns
    files = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            files.extend(glob.glob(arg))
        else:
            files.append(arg)
    
    if not files:
        print("❌ No files found")
        sys.exit(1)
    
    passed = 0
    failed = 0
    
    for file_path in sorted(files):
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            failed += 1
            continue
            
        success = validate_diff(file_path)
        if success:
            passed += 1
        else:
            failed += 1
        
        if len(files) > 1:
            print()  # Space between files
    
    # Final summary
    if len(files) > 1:
        print("=" * 60)
        print(f"📊 Summary: {passed} passed, {failed} failed")
        
    if failed > 0:
        print(f"\n💡 Fix errors and run again before committing.")
        sys.exit(1)
    else:
        print(f"\n🎉 All validations passed! Ready to commit.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n⚠️  Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)