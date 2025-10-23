# Recipe Ingestion Assistant

You are helping ingest a new Kyphi recipe into the recipe-aligner database.

This command will guide you through:
1. Parsing recipe text
2. Resolving ingredients against existing slugs
3. Updating equivalence groups
4. Generating validated diff JSON
5. Committing to git

---

## STEP 1: GATHER RECIPE TEXT

If the user hasn't already provided recipe text, ask them to paste it now.

The recipe should include:
- Source/citation information
- List of ingredients (with amounts if available)
- Any preparation notes

---

## STEP 2: LOAD CONTEXT

Run the following command to load all existing slugs and equivalences:

```bash
python scripts/assist_ingestion.py --export-all
```

Parse the output carefully. You'll need:
- **Existing ingredient slugs** - to avoid duplicates and enable matching
- **Equivalence groups** - to suggest which groups new ingredients belong to

---

## STEP 3: EXTRACT RECIPE METADATA

From the user's recipe text, extract:

1. **Recipe slug** (kebab-case, e.g., "plutarch-isis-osiris")
   - Ask user for confirmation

2. **Recipe label** (human-readable, e.g., "Plutarch, Isis and Osiris 383E-384C")

3. **Source citation** (full reference)

4. **Language code**:
   - `grc` = Ancient Greek
   - `egy` = Egyptian
   - `la` = Latin
   - `en` = English

5. **Date** (numeric, negative for BCE, e.g., -100 for 100 BCE)

---

## STEP 4: RESOLVE INGREDIENTS (CRITICAL!)

For EACH ingredient mentioned in the recipe:

### A. Extract ingredient information
- Original text/label from recipe
- Amount (raw text, value, unit)
- Preparation notes
- Any context

### B. Find existing slug OR create new one

**First, try fuzzy matching**:
```bash
python scripts/assist_ingestion.py --fuzzy-match "ingredient text here"
```

This will return similar ingredients with similarity scores.

**Present options to user**:
```
Ingredient: "σμύρνη" (from recipe)

Found existing matches:
  [1] smyrne (σμύρνη) - 95% match
      Language: grc
      In equivalence group: "Myrrh"

  [2] smyrna (σμύρνα) - 85% match
      Language: grc
      In equivalence group: "Myrrh"

Options:
  • Use existing slug [enter number 1-2]
  • Create new slug [enter 'new']
  • Skip this ingredient [enter 'skip']

Your choice:
```

### C. If creating NEW slug:

1. Ask user for the normalized label (the canonical form they want to use)

2. Suggest a slug:
```bash
python scripts/assist_ingestion.py --suggest-slug "σμύρνη" --lang grc
```

3. Validate it doesn't already exist:
```bash
python scripts/assist_ingestion.py --validate-slug "suggested-slug"
```

4. If it exists, prompt user for a different slug or reconsider using the existing one

### D. Handle aliases

For the selected slug (whether existing or new), ask user:
```
Ingredient slug: smyrne

What variant labels/aliases should we add for this ingredient in THIS recipe?
Examples:
  • English translations (e.g., "myrrh")
  • Alternative spellings (e.g., "σμύρνα")
  • Botanical identifications (e.g., "Commiphora myrrha")

Enter aliases (comma-separated), or press Enter to skip:
```

For each alias, create an entry in the "aliases" array:
```json
{
  "ingredient_slug": "smyrne",
  "variant_label": "myrrh",
  "language": "en",
  "source": "translation"
}
```

Source types: "translation", "transliteration", "identification", "variant"

---

## STEP 5: UPDATE EQUIVALENCES (INTERACTIVE)

After resolving ALL ingredients, review which equivalence groups need updating.

For each NEW ingredient OR new alias:

1. **Check if already in a group**:
```bash
python scripts/assist_ingestion.py --equivalence-for "ingredient-slug"
```

2. **If NOT in a group**, analyze and suggest:
```bash
python scripts/update_equivalences.py --suggest-for-diff diffs/temp.json
```

(You can create a temporary diff file or just analyze mentally based on aliases)

3. **Present options to user**:
```
New ingredient: smyrna (σμύρνα)
Aliases: myrrh, Commiphora myrrha

Suggested action: Add to existing group "Myrrh"
  Current members: σμύρνη, ḫrj, ꜥntj.w-šw, myrrh, dried myrrh, antjw-shw

Options:
  [1] Add to "Myrrh" group (recommended)
  [2] Create new equivalence group
  [3] Skip for now (manual update needed)

Your choice:
```

4. **Update docs/equivalences.json**

If user chooses to add to existing group:
- Read the current equivalences.json
- Add the new ingredient slug AND its label to the appropriate group
- Add any significant aliases that aren't already there

If creating new group:
- Ask for canonical group name
- Create array with slug, label, and aliases

---

## STEP 6: BUILD DIFF JSON

Now construct the diff file following data/schema_diff.json:

```json
{
  "recipes": [
    {
      "slug": "recipe-slug-here",
      "label": "Recipe Label Here",
      "source": "Full citation",
      "language": "grc",
      "date": 80
    }
  ],
  "ingredients": [
    // ONLY include NEW ingredients (not in context_slugs.json)
    {
      "slug": "new-ingredient-slug",
      "label": "Label",
      "language": "grc"
    }
  ],
  "aliases": [
    // Include ALL aliases for ALL ingredients used in this recipe
    {
      "ingredient_slug": "slug-here",
      "variant_label": "variant name",
      "language": "en",
      "source": "translation"
    }
  ],
  "entries": [
    // One entry for each ingredient in the recipe
    {
      "recipe_slug": "recipe-slug-here",
      "ingredient_slug": "ingredient-slug-here",
      "amount_raw": "δραχμὰς 16",
      "amount_value": 16,
      "amount_unit": "drachm",
      "preparation": "powdered",
      "notes": "best quality",
      "source_citation": "Full citation",
      "source_span": "383E.1"
    }
  ]
}
```

**Important**:
- `amount_raw`: the exact text from the recipe (null if not specified)
- `amount_value`: numeric value (null if not specified)
- `amount_unit`: standardized unit (null if not specified)
- `preparation`: how ingredient is prepared
- `notes`: any additional context
- `source_citation`: where this specific entry comes from
- `source_span`: specific location in source (page, line, etc.)

Save to: `diffs/YYYY-MM-DD-{recipe-slug}.json` where YYYY-MM-DD is today's date.

---

## STEP 7: VALIDATE

Run validation:
```bash
python scripts/validate_diff.py diffs/YYYY-MM-DD-recipe-slug.json
```

If validation fails:
- Fix errors
- Re-validate
- Repeat until clean

---

## STEP 8: COMMIT TO GIT

Create git commit with:
1. The new diff file
2. Updated docs/equivalences.json (if modified)

```bash
git add diffs/YYYY-MM-DD-recipe-slug.json
git add docs/equivalences.json  # if modified
git commit -m "Add [recipe-label] recipe

- X ingredients
- Y entries
- Z new aliases
- Source: [source citation]"
git push
```

---

## STEP 9: SUMMARY

Tell the user:

```
✅ Recipe ingestion complete!

📄 Diff file: diffs/YYYY-MM-DD-recipe-slug.json
📊 Statistics:
   • X ingredients (Y new)
   • Z aliases added
   • N entries

🔗 Equivalences:
   • Updated M equivalence groups

🚀 Pushed to GitHub
   • CI will auto-process in ~2 minutes
   • Check: https://github.com/[user]/recipe-aligner/actions

🌐 Once deployed, view at:
   • https://[user].github.io/recipe-aligner/
```

---

## IMPORTANT REMINDERS

1. **Slugs are LEMMATIC** (transcriptive, normalized forms)
   - σμύρνη → smyrne
   - σμύρνα → smyrna (different spelling = different slug)
   - Both are semantically "myrrh" but get separate slugs

2. **Equivalences are SEMANTIC** (real-world substances)
   - Groups together different slugs that refer to the same thing
   - "Myrrh" group includes: smyrne, smyrna, xrj, antjw-shw, plus aliases

3. **Always validate slugs** before using them
   - Check context_slugs.json via fuzzy matching
   - Don't hallucinate slugs!

4. **Aliases are flexible**
   - Translations, variants, identifications all go in aliases
   - Can have multiple aliases per ingredient
   - Each alias needs language + source

5. **Be interactive**
   - Always confirm with user before creating new slugs
   - Present options, don't assume
   - Scholarly judgment is required for equivalences

---

## TROUBLESHOOTING

**"Validation failed - unknown ingredient_slug"**
- Check that ingredient slug exists in context_slugs.json OR is in the diff's "ingredients" array

**"Aliases reference unknown ingredients"**
- Make sure alias.ingredient_slug matches either existing or new ingredient

**"Equivalence group contains unknown term"**
- Validate equivalences after updating:
  ```bash
  python scripts/update_equivalences.py --validate
  ```

**"Fuzzy match returns nothing"**
- Ingredient is genuinely new - create new slug
- Try searching for aliases (English translation, etc.)

---

## QUICK REFERENCE

```bash
# Load context
python scripts/assist_ingestion.py --export-all

# Fuzzy match
python scripts/assist_ingestion.py --fuzzy-match "text"

# Validate slug
python scripts/assist_ingestion.py --validate-slug "slug"

# Suggest slug
python scripts/assist_ingestion.py --suggest-slug "label" --lang grc

# Check equivalence
python scripts/assist_ingestion.py --equivalence-for "term"

# Validate diff
python scripts/validate_diff.py diffs/file.json

# Validate equivalences
python scripts/update_equivalences.py --validate
```

---

Now begin the ingestion process!
