# Recipe Amendment Plan

## Problem Statement

Two issues discovered with Aetius recipes:

### 1. Missing Entry in Aetius Kyphi 28
**Original text:** "ἐν ἄλλῳ καὶ κασίας αʹ"
**Translation:** "in another [recipe/variant], also cassia 1 [ounce]"
**Issue:** κασία (kasia) was included in ingredients/aliases but missing from entries
**Status:** Ingredient exists in DB, just needs entry added

### 2. Missing Optional Ingredient in Aetius Kyphi 36
**Original text:** "σχοίνου ἄνθους ἢ ἀσπαλάθου ἀνὰ οὐγγίαν αʹ"
**Translation:** "of schoinos flower or aspalathos, 1 ounce each"
**Issue:** Text indicates "or" (ἢ) suggesting optional/alternative ingredients
**Current status:** May have been parsed incorrectly - needs investigation

## Analysis

### Root Cause
The ingestion missed ingredients with markers like:
- "ἐν ἄλλῳ" (in another [variant])
- "ἢ" (or) suggesting alternatives/options

These markers indicate:
1. **Variants** - ingredients that appear in alternative versions
2. **Options** - ingredients that can substitute for each other

### Current Schema Limitations
Neither `schema_diff.json` nor `schema_master.json` have:
- `optional` flag on entries
- `variant` flag on entries
- `alternatives` grouping

## Proposed Solutions

### Option A: Use `notes` Field (Quick Fix)
**Pros:**
- No schema changes required
- Can be implemented immediately
- Backward compatible

**Cons:**
- Not structured/queryable
- Inconsistent formatting possible
- Harder to filter in UI

**Implementation:**
```json
{
  "recipe_slug": "aetius-kyphi-28",
  "ingredient_slug": "kasia",
  "amount_raw": "αʹ",
  "amount_value": 1,
  "amount_unit": "ounce",
  "preparation": null,
  "notes": "listed as optional (ἐν ἄλλῳ - in another variant)",
  "source_citation": "Aetius of Amida 13.117",
  "source_span": "13.117"
}
```

### Option B: Add `optional` Boolean Field (Medium)
**Pros:**
- Structured and queryable
- Clear semantics
- Easy to filter in UI

**Cons:**
- Requires schema migration
- Need to update all existing entries (add `optional: false`)
- More complex validation

**Implementation:**
1. Update `data/schema_master.json` - add `"optional": { "type": "boolean", "default": false }`
2. Update `data/schema_diff.json` - add `"optional": { "type": ["boolean", "null"] }`
3. Migrate MASTER.json - add `"optional": false` to all existing entries
4. Update merge_diff.py to handle optional field
5. Update export_long.py to export optional flag

### Option C: Add `alternative_group` Field (Complex)
**Pros:**
- Most semantically rich
- Can group alternatives (e.g., "schoinos OR aspalathos")
- Future-proof for complex variants

**Cons:**
- Most complex to implement
- Requires new grouping logic
- May be overkill for current needs

## Recommended Approach

### Phase 1: Quick Fix (Immediate)
Use **Option A** (notes field) for current amendments:
- Add missing kasia entry to Aetius 28 with note
- Review Aetius 36 for missing alternatives with notes

### Phase 2: Structured Solution (Future)
Implement **Option B** (optional boolean):
- Schema update PR
- Migration script for existing data
- Update validation and export scripts
- Update web UI to show optional ingredients

## Amendment Workflow Design

### Question: Remove & Replace vs. Patch?

**Option 1: Remove & Replace (scripts/remove_diff.py + new diff)**
- Use existing `remove_diff.py` to remove the original diff
- Create new corrected diff with all entries
- Re-merge to MASTER.json

**Pros:**
- Clean audit trail
- Uses existing tooling
- No risk of partial state

**Cons:**
- Removes and re-adds ALL entries (not just missing one)
- Changes all entry_ids
- Breaks referential integrity if anything references old IDs

**Option 2: Create Amendment Diff (new pattern)**
- Create a new diff type: "amendment"
- Contains only the missing/corrected entries
- Special merge logic to add/update specific entries

**Pros:**
- Minimal changes to MASTER
- Preserves existing entry_ids
- Surgical precision

**Cons:**
- Need new tooling (merge_amendment.py)
- More complex to validate
- Risk of inconsistency

**Option 3: Manual MASTER.json Edit + Document**
- Directly edit MASTER.json to add missing entries
- Document in git commit
- Update processed diff for reference

**Pros:**
- Fastest for small changes
- No new tooling needed
- Clear what changed

**Cons:**
- Breaks the "diffs → MASTER" paradigm
- Can't replay from diffs alone
- Error-prone (manual ID assignment)

### Recommendation: **Option 3 for Phase 1**

For this immediate fix:
1. Manually edit MASTER.json to add the missing entries
2. Get next available entry_id
3. Add entries with proper IDs
4. Update the processed diff files for documentation
5. Commit with clear message
6. Export to kyphi_long.json

For future amendments, consider building Option 2 (amendment diff tooling).

## Implementation Steps

### Step 1: Investigate Current State
```bash
# Check what's in MASTER for Aetius 28
jq '.entries[] | select(.recipe_id == X)' data/MASTER.json | wc -l

# Check recipe_id for aetius-kyphi-28
jq '.recipes[] | select(.slug == "aetius-kyphi-28")' data/MASTER.json

# Find next available entry_id
jq '.entries | map(.entry_id) | max' data/MASTER.json
```

### Step 2: Prepare Amendment Data
- Aetius 28: Add kasia entry (ingredient_id for kasia = ?)
- Aetius 36: Review and add any missing alternatives

### Step 3: Edit MASTER.json
- Add new entries with incremented entry_ids
- Add notes field indicating "listed as optional"

### Step 4: Update Processed Diffs
- Update the processed diff files to match
- Maintain documentation consistency

### Step 5: Export and Deploy
```bash
python3 scripts/export_long.py data/MASTER.json docs/kyphi_long.json
git add data/MASTER.json docs/kyphi_long.json diffs/processed/*.json
git commit -m "fix: add missing optional ingredients to Aetius recipes"
git push
```

### Step 6: Update Ingestion Logic
Update `.claude/commands/ingest-recipe.md` to detect:
- "ἐν ἄλλῳ" markers → add note "listed as optional (in another variant)"
- "ἢ" (or) markers → add note "listed as alternative"
- Ensure all ingredients in ingredients[] have corresponding entries[]

## Future Enhancements

### Detection Patterns for Optional Ingredients
Greek markers to watch for:
- `ἐν ἄλλῳ` - in another [variant]
- `ἢ` - or
- `καὶ` - also/and (sometimes indicates addition)
- `ἀντὶ` - instead of
- `ἢ ἄλλως` - or otherwise

### Schema Evolution Path
1. Phase 1: Use notes field (current)
2. Phase 2: Add optional boolean + migration
3. Phase 3: Consider alternative_group for complex cases
4. Phase 4: UI updates to filter/highlight optional ingredients

## Questions for User

1. **Schema change timing:** Should we implement optional boolean now, or use notes field for quick fix?
2. **Amendment workflow:** Should we build amendment diff tooling for future, or always use manual edits?
3. **Alternative handling:** How should we represent "X or Y" alternatives? Separate entries with notes, or grouped?
4. **UI requirements:** How should optional ingredients display in the web app?
