# Recipe Ingestion Guide

Complete guide for ingesting new Kyphi recipes into the recipe-aligner database.

## Quick Start

The fastest way to ingest a recipe is using the Claude Code slash command:

```bash
/ingest-recipe
```

This interactive command will guide you through the entire process.

---

## Understanding the Data Model

### Layer 1: Slugs (Lemmatic/Transcriptive)

**Slugs** are normalized transcriptions of ingredient names in their original language.

Examples:
- Greek `σμύρνη` → slug: `smyrne`
- Greek `σμύρνα` → slug: `smyrna` (different spelling = different slug)
- Egyptian `ḫrj` → slug: `xrj`
- Egyptian `ꜥntj.w-šw` → slug: `antjw-shw`

**Key principle**: Each unique textual form gets its own slug, even if semantically equivalent.

### Layer 2: Equivalences (Semantic)

**Equivalence groups** link different slugs that refer to the same real-world substance.

Example - "Myrrh" equivalence group:
```json
{
  "Myrrh": [
    "σμύρνη",      // Greek label (slug: smyrne)
    "σμύρνα",      // Greek label (slug: smyrna)
    "ḫrj",         // Egyptian label (slug: xrj)
    "ꜥntj.w-šw",   // Egyptian label (slug: antjw-shw)
    "smyrne",      // The Greek slug itself
    "smyrna",      // The other Greek slug
    "xrj",         // The Egyptian slug
    "antjw-shw",   // The other Egyptian slug
    "myrrh",       // English alias
    "dried myrrh"  // English variant
  ]
}
```

---

## Workflow Overview

### Step 1: Prepare Recipe Text

Have ready:
- ✅ Source citation
- ✅ Original language text (if applicable)
- ✅ Ingredient list
- ✅ Amounts and preparations (if available)
- ✅ Date/time period
- ✅ Language code (grc, egy, la, en)

### Step 2: Run /ingest-recipe

In Claude Code:
```
/ingest-recipe
```

Paste your recipe text when prompted.

### Step 3: Interactive Ingredient Resolution

For each ingredient, the system will:

1. **Search existing slugs** using fuzzy matching
2. **Show similarity scores** and equivalence groups
3. **Ask you to choose**:
   - Use existing slug
   - Create new slug
   - Skip ingredient

### Step 4: Update Equivalences

For new ingredients or aliases:

1. System suggests which equivalence group to add to
2. You confirm or create new group
3. `docs/equivalences.json` is updated automatically

### Step 5: Validate & Commit

System will:
1. Generate diff JSON
2. Validate against schema
3. Commit to git
4. Push to GitHub

GitHub CI then:
1. Merges to MASTER.json
2. Exports to web app
3. Deploys to GitHub Pages

---

## Slug Creation Rules

### Greek (grc)

1. Remove diacritics: `ά → a`, `ή → e`
2. Transliterate:
   - `α → a`, `β → b`, `γ → g`, `δ → d`, `ε → e`
   - `ζ → z`, `η → e`, `θ → th`, `ι → i`, `κ → k`
   - `λ → l`, `μ → m`, `ν → n`, `ξ → x`, `ο → o`
   - `π → p`, `ρ → r`, `σ/ς → s`, `τ → t`, `υ → y`
   - `φ → ph`, `χ → ch`, `ψ → ps`, `ω → o`
3. Use nominative/lemmatic form
4. Example: `κιννάμωμον → kinnamomon`

### Egyptian (egy)

1. Use standard Egyptological transcription
2. Replace special chars for URL safety:
   - Dots (`.`) → remove or convert to `-`
   - Braces (`{}[]`) → remove
3. Example: `ꜥntj.w-šw → antjw-shw`

### Latin/English

1. Convert to lowercase
2. Replace spaces/special chars with hyphens
3. Example: `Commiphora myrrha → commiphora-myrrha`

---

## Helper Tools Reference

### Fuzzy Match Ingredients

Find similar existing ingredients:

```bash
python3 scripts/assist_ingestion.py --fuzzy-match "myrrh"
```

Output:
```
Found 5 similar ingredients:

  [1] antjw-shw
      Label: ꜥntj.w-šw (via alias: myrrh)
      Language: en
      Similarity: 100% [in group: Myrrh]

  [2] xrj
      Label: ḫrj (via alias: myrrh)
      Language: en
      Similarity: 100%
  ...
```

### Validate Slug Exists

Check if a slug is already in use:

```bash
python3 scripts/assist_ingestion.py --validate-slug "smyrne"
```

### Suggest New Slug

Auto-generate slug from label:

```bash
python3 scripts/assist_ingestion.py --suggest-slug "σμύρνη" --lang grc
```

Output:
```
💡 Suggested slug: smyrne
   From: σμύρνη (grc)
   ⚠️  Warning: This slug already exists!
```

### Check Equivalence Groups

See which group contains a term:

```bash
python3 scripts/assist_ingestion.py --equivalence-for "myrrh"
```

Output:
```
✅ Found in equivalence group: 'Myrrh'

All terms in 'Myrrh':
  • σμύρνη
  • ḫrj
  • ꜥntj.w-šw
  • myrrh
  • dried myrrh
  ...
```

### Export Full Context

Get all existing slugs and equivalences:

```bash
python3 scripts/assist_ingestion.py --export-all
```

---

## Equivalence Management

### Suggest Updates for Diff

Analyze a diff file and suggest equivalence updates:

```bash
python3 scripts/update_equivalences.py --suggest-for-diff diffs/new-recipe.json
```

### Interactive Mode

Manually build/update equivalence groups:

```bash
python3 scripts/update_equivalences.py --interactive
```

### Validate Equivalences

Check that all terms in equivalences exist in MASTER:

```bash
python3 scripts/update_equivalences.py --validate
```

---

## Diff File Structure

Your diff file should follow this structure:

```json
{
  "recipes": [
    {
      "slug": "recipe-slug",
      "label": "Human Readable Recipe Name",
      "source": "Full citation",
      "language": "grc",
      "date": 80
    }
  ],
  "ingredients": [
    // ONLY new ingredients not in context_slugs.json
    {
      "slug": "new-ingredient-slug",
      "label": "Original label",
      "language": "grc"
    }
  ],
  "aliases": [
    // ALL aliases for ingredients in this recipe
    {
      "ingredient_slug": "ingredient-slug",
      "variant_label": "translation or variant",
      "language": "en",
      "source": "translation"
    }
  ],
  "entries": [
    // One per ingredient in the recipe
    {
      "recipe_slug": "recipe-slug",
      "ingredient_slug": "ingredient-slug",
      "amount_raw": "δραχμὰς 16",
      "amount_value": 16,
      "amount_unit": "drachm",
      "preparation": "powdered",
      "notes": "additional context",
      "source_citation": "Specific citation",
      "source_span": "383E.1"
    }
  ]
}
```

### Field Guidelines

**Recipes:**
- `slug`: kebab-case, unique identifier
- `label`: human-readable name
- `source`: full bibliographic citation
- `language`: ISO 639-3 code (grc, egy, la, en)
- `date`: numeric year (negative for BCE)

**Ingredients:**
- Only include if genuinely new
- `slug`: following language-specific rules
- `label`: original form from source
- `language`: ISO 639-3 code

**Aliases:**
- `ingredient_slug`: must exist in context_slugs.json or diff ingredients
- `variant_label`: translation, variant, or identification
- `language`: language of the variant
- `source`: "translation", "transliteration", "identification", "variant"

**Entries:**
- `amount_raw`: exact text from source (null if not specified)
- `amount_value`: numeric value (null if not specified)
- `amount_unit`: standardized unit
- `preparation`: how ingredient is prepared
- `notes`: scholarly notes, uncertainties
- `source_citation`: specific reference
- `source_span`: page/line/section number

---

## Troubleshooting

### "Validation failed - unknown ingredient_slug"

**Problem**: Alias or entry references an ingredient that doesn't exist.

**Solution**:
1. Check slug is in `context_slugs.json`:
   ```bash
   python3 scripts/assist_ingestion.py --validate-slug "your-slug"
   ```
2. OR ensure it's in your diff's `ingredients` array

### "Fuzzy match returns nothing"

**Problem**: Ingredient is genuinely new.

**Solution**:
1. Try searching for English translation
2. Try searching for related ingredients
3. If still nothing, create new slug:
   ```bash
   python3 scripts/assist_ingestion.py --suggest-slug "label" --lang grc
   ```

### "Equivalence validation failed"

**Problem**: Equivalence group contains unknown term.

**Solution**:
1. Run validation to see errors:
   ```bash
   python3 scripts/update_equivalences.py --validate
   ```
2. Check if term exists as slug, label, or alias in MASTER
3. Fix typos in `docs/equivalences.json`

### "CI validation failed"

**Problem**: GitHub Actions couldn't process your diff.

**Solution**:
1. Check Actions tab for detailed error
2. Run local validation:
   ```bash
   python3 scripts/validate_diff.py diffs/your-file.json
   ```
3. Fix errors and push again

---

## Best Practices

### ✅ DO

- Always fuzzy-match before creating new slugs
- Validate slugs don't already exist
- Add comprehensive aliases (translations, identifications)
- Update equivalence groups during ingestion
- Include detailed source citations
- Use null for missing/unknown values
- Test validation locally before pushing

### ❌ DON'T

- Create slugs without checking existing ones
- Hallucinate slugs (always use context_slugs.json)
- Skip equivalence updates for new ingredients
- Use empty strings for missing data (use null)
- Commit without validation
- Update MASTER.json directly (use diffs)

---

## Example: Complete Ingestion

Let's walk through ingesting a fictional recipe.

### 1. Prepare Recipe

```
Source: Dioscorides, De Materia Medica 1.30
Language: Ancient Greek
Date: 70 CE

Ingredients:
- μύρρα (myrrha) - 12 drachmas
- μέλι (honey) - amount not specified
- οἶνος (wine) - for mixing
```

### 2. Run /ingest-recipe

```
/ingest-recipe
```

Paste the above text.

### 3. Extract Metadata

Claude will extract:
- Recipe slug: `dioscorides-130` (you confirm)
- Label: `Dioscorides, De Materia Medica 1.30`
- Source: `Dioscorides 1.30 (Wellmann)`
- Language: `grc`
- Date: `70`

### 4. Resolve Ingredients

**Ingredient 1: μύρρα**

Fuzzy match finds: `smyrne`, `smyrna`, `xrj`, `antjw-shw` (all "myrrh")

You choose: `[1] smyrne` (existing slug)

Aliases to add:
- `myrrh` (English, translation)
- `μύρρα` (Greek variant of μύρνη)

**Ingredient 2: μέλι**

Fuzzy match finds: `meli` (existing slug for honey)

You choose: `[1] meli`

Aliases: (already has "honey")

**Ingredient 3: οἶνος**

Fuzzy match finds: `oinos` (existing slug for wine)

You choose: `[1] oinos`

### 5. Update Equivalences

System suggests:
- Add `μύρρα` to "Myrrh" group → You accept
- `meli` and `oinos` already in groups → Skip

### 6. Generate Diff

System creates `diffs/2025-10-23-dioscorides-130.json`

### 7. Validate

```bash
python3 scripts/validate_diff.py diffs/2025-10-23-dioscorides-130.json
```

✅ Passes

### 8. Commit & Push

```bash
git add diffs/2025-10-23-dioscorides-130.json docs/equivalences.json
git commit -m "Add Dioscorides 1.30 recipe"
git push
```

### 9. CI Processes

GitHub Actions:
1. Validates diff
2. Merges to MASTER.json
3. Exports to kyphi_long.json
4. Commits changes
5. Deploys to GitHub Pages

✅ Done! Recipe is now live.

---

## Getting Help

- **Slash command not working?** Make sure `.claude/commands/ingest-recipe.md` exists
- **Python errors?** Check you're using Python 3.8+
- **Data questions?** Check `docs/equivalences.json` for semantic groupings
- **CI issues?** Check GitHub Actions logs

For more help, open an issue at: https://github.com/alchemiesofscent/recipe-aligner/issues
