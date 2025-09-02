# Kyphi Recipe Aligner

A comprehensive web-based tool for aligning and comparing ancient kyphi incense recipes across different sources, with a professional data workflow powered by GitHub automation.

## 🌐 **Live Demo**

Visit the app at: `https://alchemiesofscent.github.io/kyphi-repo/`

## ✨ **Key Features**

- **🔍 Interactive Search**: Find ingredients across recipes with live search and filtering
- **📊 Smart Alignment**: Compare recipe variations side-by-side in a clean table view  
- **🤖 Automated Workflow**: CI/CD pipeline handles validation, merging, and deployment
- **🗂️ Data Integrity**: Prevents duplicates and maintains referential integrity
- **📱 Mobile-Friendly**: Responsive design works on all devices
- **🌍 Unicode Support**: Proper handling of ancient Greek, Arabic, and other scripts
- **📤 Export Options**: Download data as CSV or JSON with one click
- **🔄 Version Control**: Full audit trail of all changes via Git

## 📁 **Repository Structure**

```
kyphi-repo/
├── docs/                          # 🌐 GitHub Pages site
│   ├── index.html                # Main aligner web app
│   └── kyphi_long.json           # Auto-generated data (don't edit!)
├── data/                          # 📚 Core database
│   ├── MASTER.json               # Canonical database (don't edit by hand!)
│   ├── schema_master.json        # Schema for MASTER.json
│   └── schema_diff.json          # Schema for diff files
├── diffs/                         # 📥 Ingestion files
│   ├── 2025-09-01-rufus.json     # Example diff file
│   └── processed/                # Auto-archived completed diffs
├── scripts/                       # 🛠️ Data processing tools
│   ├── merge_diff.py             # Merges diffs into MASTER.json (enhanced!)
│   ├── export_long.py            # Exports MASTER to web format (enhanced!)
│   ├── remove_diff.py            # Removes diffs from MASTER.json (new!)
│   └── validate_diff.py          # Local validation tool (new!)
└── .github/workflows/
    └── ci.yml                    # GitHub Actions workflow (enhanced!)
```

## 🔄 **Workflow Overview**

### **1. Data Ingestion**
```mermaid
graph LR
    A[Create Diff JSON] --> B[Validate Locally]
    B --> C[Open Pull Request]
    C --> D[CI Validates & Previews]
    D --> E[Merge to Main]
    E --> F[Auto-Deploy to GitHub Pages]
```

### **2. Step-by-Step Process**
1. **📝 Create diff files** following the schema (see examples below)
2. **✅ Validate locally** using `python scripts/validate_diff.py diffs/my_diff.json`
3. **📋 Open Pull Request** - CI shows validation results and merge preview  
4. **🔍 Review & merge** - changes are automatically applied and deployed
5. **🌐 Visit live site** - updates appear within minutes

## 🚀 **Quick Start**

### **Setup Repository**
```bash
# Clone and setup
git clone https://github.com/[username]/[repo-name]
cd [repo-name]

# Test with sample data
python scripts/merge_diff.py data/MASTER.json diffs/example_2025-09-01.json "test"
python scripts/export_long.py data/MASTER.json docs/kyphi_long.json

# Run locally
cd docs && python -m http.server 8000
# Visit http://localhost:8000
```

### **Enable GitHub Pages**
1. Go to repo **Settings → Pages**  
2. Source: **Deploy from branch**
3. Branch: **main** / Folder: **/ docs**
4. Save and wait ~5 minutes for deployment

### **Your First Diff**
Create `diffs/2025-09-02-my-source.json`:

```json
{
  "recipes": [{
    "slug": "dioscorides-kyphi", 
    "label": "Dioscorides Kyphi",
    "source": "De Materia Medica",
    "language": "ancient_greek"
  }],
  "ingredients": [{
    "slug": "myrrh",
    "label": "σμύρνα", 
    "language": "grc"
  }],
  "aliases": [{
    "ingredient_slug": "myrrh",
    "variant_label": "myrrh",
    "language": "en"
  }],
  "entries": [{
    "recipe_slug": "dioscorides-kyphi",
    "ingredient_slug": "myrrh",
    "amount_raw": "δραχμὰς 16",
    "amount_value": 16,
    "amount_unit": "drachm",
    "preparation": "powdered",
    "notes": "best quality"
  }]
}
```

## 🛠️ **Local Development Tools**

### **Enhanced Scripts with Rich Feedback**

```bash
# Validate diff files (comprehensive checking)
python scripts/validate_diff.py diffs/my_diff.json
python scripts/validate_diff.py diffs/*.json  # validate all

# Merge with detailed progress reporting  
python scripts/merge_diff.py data/MASTER.json diffs/my_diff.json "my_source"

# Export with statistics and validation
python scripts/export_long.py data/MASTER.json docs/kyphi_long.json

# Remove entries (undo a diff)
python scripts/remove_diff.py data/MASTER.json diffs/my_diff.json "removal_reason"
```

### **All Scripts Now Provide:**
- ✅ **Rich visual feedback** with emojis and progress indicators
- 📊 **Detailed statistics** (before/after counts, summaries)
- ⚠️ **Clear error messages** with specific guidance
- 💡 **Helpful suggestions** for improvements
- 🔍 **Data quality checks** (duplicates, missing fields, etc.)

## 📋 **Data Schema Reference**

### **Diff Format (`diffs/*.json`)**
```json
{
  "recipes": [
    {
      "slug": "unique-recipe-id",      // required: URL-safe identifier
      "label": "Display Name",         // required: human-readable name
      "language": "en",                // optional: ISO language code  
      "source": "Book/Author"          // optional: citation
    }
  ],
  "ingredients": [
    {
      "slug": "unique-ingredient-id",  // required: URL-safe identifier
      "label": "Display Name",         // required: human-readable name
      "language": "grc"                // optional: ISO language code
    }
  ],
  "aliases": [
    {
      "ingredient_slug": "myrrh",      // required: references ingredients
      "variant_label": "sweet myrrh",  // required: alternative name
      "language": "en",                // optional: language of variant
      "source": "Translation"          // optional: source of variant
    }
  ],
  "entries": [
    {
      "recipe_slug": "recipe-id",      // required: references recipes
      "ingredient_slug": "myrrh",      // required: references ingredients  
      "amount_raw": "2 drachms",       // optional: original text
      "amount_value": 2,               // optional: numeric value
      "amount_unit": "drachm",         // optional: unit of measurement
      "preparation": "ground fine",    // optional: preparation method
      "notes": "best quality only",    // optional: additional notes
      "source_citation": "Book 1.64",  // optional: specific citation
      "source_span": "lines 12-15"    // optional: location in source
    }
  ]
}
```
## 🛠 **Requirements**

- Python 3.7+
- `jsonschema` library for validation

## 🔧 **Advanced Features**

### **Data Management**
- **🔄 Smart Deduplication**: Prevents duplicate entries across all entity types
- **🆔 Stable IDs**: Each entity gets permanent numeric IDs for reliable referencing  
- **📅 Provenance Tracking**: Records when/how each entry was added
- **🗑️ Safe Removal**: Remove diffs without breaking references
- **✅ Referential Integrity**: Validates all slug references

### **Web App Enhancements**
- **🔍 Live Search**: Real-time filtering with visual feedback
- **📊 Dynamic Table**: Recipe selection with ingredient alignment
- **📤 Fixed CSV Export**: Now generates proper CSV format (was broken!)
- **💬 Toast Notifications**: Success/error messages for user actions
- **🎨 Better UX**: Loading states, empty states, error recovery
- **📱 Mobile Responsive**: Works great on phones and tablets

### **CI/CD Pipeline**  
- **✅ Schema Validation**: Ensures all diffs conform to expected structure
- **🧪 Dry-Run Preview**: Shows exactly what changes will happen before merge
- **📊 Statistics Reporting**: Before/after counts in CI logs
- **📁 Auto-Archiving**: Moves processed diffs to `diffs/processed/` 
- **🚀 Zero-Downtime Deployment**: Changes appear live within minutes

## 🐛 **Troubleshooting**

### **Common Issues**
```bash
# JSON validation errors
python scripts/validate_diff.py diffs/my_diff.json

# Reference errors (unknown slugs)
# Check that recipe_slug/ingredient_slug exist in recipes/ingredients arrays

# Empty web app
python scripts/export_long.py data/MASTER.json docs/kyphi_long.json
cd docs && python -m http.server 8000

# CI failing
# Check GitHub Actions tab for detailed error logs
```

### **Data Quality Checks**
- ⚠️ **Duplicate slugs** within a single diff
- ❌ **Missing required fields** (slug, label)
- 🔗 **Broken references** (unknown recipe_slug/ingredient_slug)
- 📝 **Short labels** (< 2-3 characters)
- 🌍 **Missing language tags** for non-ASCII content

## 🤝 **Contributing**

### **For Recipe Data**
1. **Fork** the repository
2. **Create** a new diff file in `diffs/YYYY-MM-DD-source.json`
3. **Validate** locally: `python scripts/validate_diff.py diffs/your_diff.json`
4. **Open** a Pull Request with description of the source
5. **Review** CI results and address any issues
6. **Merge** when approved - changes deploy automatically!

### **For Code Improvements**
- All scripts have comprehensive error handling and user feedback
- Web app includes fallbacks and graceful error recovery  
- CI pipeline provides detailed validation and preview
- Follow existing patterns for consistency

## 📊 **System Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Diff Files    │───▶│   MASTER.json    │───▶│  Web App Data   │
│  (Slug-based)   │    │   (ID-based)     │    │ (Label-based)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        ▲                        ▲                        ▲
        │                        │                        │
   📝 Human Input           🤖 CI Pipeline          🌐 GitHub Pages

Schema Validation ──▶ Deduplication ──▶ ID Assignment ──▶ Export ──▶ Deploy
```

The system transforms human-friendly slug-based diffs into a normalized database with stable numeric IDs, then exports a flattened view perfect for web consumption.

## 📈 **Roadmap**

- [ ] **Search improvements**: Fuzzy matching, advanced filters
- [ ] **Data visualization**: Charts showing ingredient frequency, recipe relationships  
- [ ] **API endpoint**: Programmatic access to the dataset
- [ ] **Bulk import**: Tools for processing large datasets
- [ ] **Mobile app**: Native iOS/Android companion

---

**Built with ❤️ for digital humanities research**

For support, open an issue or check the [GitHub Discussions](https://github.com/alchemiesofscent/kyphi-repo/discussions) tab.

