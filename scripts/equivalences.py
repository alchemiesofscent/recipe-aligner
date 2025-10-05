#!/usr/bin/env python3
"""
Unified equivalences tool.

Subcommands:
  - auto  : Build draft groups from MASTER aliases (English), include labels (Greek/Latin) and lemmas; write data/equivalences_auto.json.
  - diff  : Compare draft vs curated docs/equivalences.json; show adds/removals.
  - merge : Merge draft into curated using alias map (data/equivalences_alias_map.json); dry-run by default; use --write to save.

This script NEVER overwrites docs/equivalences.json automatically without --write.
"""

from __future__ import annotations
import argparse
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

from lemma import lemmatize, load_overrides

ROOT = os.path.dirname(os.path.dirname(__file__))
MASTER_PATH = os.path.join(ROOT, 'data', 'MASTER.json')
AUTO_PATH = os.path.join(ROOT, 'data', 'equivalences_auto.json')
CURATED_PATH = os.path.join(ROOT, 'docs', 'equivalences.json')
ALIAS_MAP_PATH = os.path.join(ROOT, 'data', 'equivalences_alias_map.json')
OVERRIDES_PATH = os.path.join(ROOT, 'data', 'lemma_overrides.json')


def load_master() -> dict:
    with open(MASTER_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def nfkc(s: str) -> str:
    import unicodedata
    return '' if s is None else unicodedata.normalize('NFKC', str(s))


def build_auto(master: dict) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    overrides = load_overrides(OVERRIDES_PATH)
    ingredients = {i["ingredient_id"]: i for i in master.get("ingredients", [])}
    aliases = master.get("aliases", [])

    # Group by English alias (lowercased canonical key)
    english_groups: Dict[str, List[dict]] = defaultdict(list)
    for a in aliases:
        if (a.get('language') or '').lower() == 'en':
            key = nfkc(a.get('variant_label', '')).strip().lower()
            if not key:
                continue
            ing = ingredients.get(a.get('ingredient_id'))
            if not ing:
                continue
            english_groups[key].append(ing)

    # Build mapping: english key -> variants (english + all labels seen)
    mapping: Dict[str, List[str]] = {}
    lemma_map: Dict[str, str] = {}
    for key, ings in english_groups.items():
        if len(ings) < 2:
            # Only consider groups that actually connect multiple ingredients
            continue
        variants = set([key])
        for ing in ings:
            label = nfkc(ing.get('label', '')).strip()
            if label:
                variants.add(label)
                lang = (ing.get('language') or '').lower()
                lemma = lemmatize(label, lang, overrides)
                if lemma and lemma != label:
                    variants.add(lemma)
                    lemma_map[label] = lemma
        mapping[key] = sorted(variants)

    return mapping, lemma_map


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def cmd_auto(_: argparse.Namespace) -> None:
    master = load_master()
    mapping, lemma_map = build_auto(master)
    # Write draft mapping and lemmas for review
    payload = {
        "mapping": mapping,
        "lemmas": lemma_map,
        "source": "MASTER aliases (en) + labels",
    }
    write_json(AUTO_PATH, payload)
    print(f"Wrote draft equivalences to {AUTO_PATH}")
    print(f"Groups: {len(mapping)} | Lemmas: {len(lemma_map)}")


def load_curated() -> dict:
    with open(CURATED_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def cmd_diff(_: argparse.Namespace) -> None:
    if not os.path.exists(AUTO_PATH):
        print("No draft found. Run: python scripts/equivalences.py auto")
        return
    auto = json.load(open(AUTO_PATH, 'r', encoding='utf-8'))
    mapping = auto.get('mapping', {})
    curated = load_curated()

    curated_keys_lower = {k.lower(): k for k in curated.keys()}
    new_keys = [k for k in mapping.keys() if k.lower() not in curated_keys_lower]
    print(f"New alias groups not in curated: {len(new_keys)}")
    for k in sorted(new_keys)[:20]:
        print(f"  + {k} ({len(mapping[k])} variants)")

    # Show overlap and variant additions for keys that do match (case-insensitive)
    print("\nVariant additions in overlapping keys:")
    for k, variants in mapping.items():
        ck = curated_keys_lower.get(k.lower())
        if not ck:
            continue
        added = sorted(set(variants) - set(curated.get(ck, [])))
        if added:
            print(f"  * {ck}: +{len(added)}")
            for v in added[:10]:
                print(f"      - {v}")


def cmd_merge(ns: argparse.Namespace) -> None:
    if not os.path.exists(AUTO_PATH):
        print("No draft found. Run: python scripts/equivalences.py auto")
        return
    auto = json.load(open(AUTO_PATH, 'r', encoding='utf-8'))
    mapping = auto.get('mapping', {})
    curated = load_curated()
    alias_map = json.load(open(ALIAS_MAP_PATH, 'r', encoding='utf-8')) if os.path.exists(ALIAS_MAP_PATH) else {}

    # Build destination starting from curated
    dest = {k: list(v) for k, v in curated.items()}
    pending = []

    # Merge mapping into curated using alias_map (english alias -> curated key)
    for en_key, variants in mapping.items():
        target = alias_map.get(en_key)
        if not target:
            pending.append(en_key)
            continue
        existing = set(dest.get(target, []))
        added = [v for v in variants if v not in existing]
        if added:
            dest.setdefault(target, []).extend(added)
            print(f"Merged {en_key} -> {target}: +{len(added)} variants")

    if pending:
        print("\nAliases with no mapping to curated groups (add to data/equivalences_alias_map.json):")
        for k in sorted(pending):
            print(f"  - {k}")

    if ns.write:
        write_json(CURATED_PATH, dest)
        print(f"Saved merged equivalences to {CURATED_PATH}")
    else:
        print("\nDry run only (no changes written). Use --write to save.")


def main():
    p = argparse.ArgumentParser(description="Unified Equivalences Tool")
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('auto', help='Produce draft auto equivalences')
    a.set_defaults(func=cmd_auto)

    d = sub.add_parser('diff', help='Show differences between draft and curated')
    d.set_defaults(func=cmd_diff)

    m = sub.add_parser('merge', help='Merge draft into curated using alias map')
    m.add_argument('--write', action='store_true', help='Write merged result to docs/equivalences.json')
    m.set_defaults(func=cmd_merge)

    ns = p.parse_args()
    ns.func(ns)


if __name__ == '__main__':
    main()

