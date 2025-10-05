#!/usr/bin/env python3
"""
Lightweight lemmatization helpers for Greek and Latin.

Goals (non-exhaustive, safe-first):
- Provide minimal, conservative heuristics for nominative singular linking.
- Allow curated overrides via data/lemma_overrides.json to correct/extend.
- Never mutate persisted data automatically; this is used by tools for grouping.
"""

from __future__ import annotations
import json
import os
import unicodedata
from typing import Dict

ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_OVERRIDES_PATH = os.path.join(ROOT, 'data', 'lemma_overrides.json')


def strip_diacritics(text: str) -> str:
    if text is None:
        return ''
    text = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in text if not unicodedata.combining(c))


def load_overrides(path: str = DEFAULT_OVERRIDES_PATH) -> Dict[str, str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _lemmatize_greek(label: str) -> str:
    # Extremely conservative heuristics; rely on overrides for tricky cases.
    s = label.strip()
    # Common genitive singular -> nominative singular for 2nd declension -ος
    # e.g., κυπέρου -> κύπειρος
    if s.endswith('ου') and ' ' not in s:
        return s[:-2] + 'ος'
    # Default: unchanged
    return s


def _lemmatize_latin(label: str) -> str:
    s = label.strip()
    # Noun phrase helpers (very light):
    # -i -> -us (e.g., costi -> costus), but avoid false positives by whitelisting.
    WHITELIST_I_TO_US = {'costi', 'cardamomi'}
    if s in WHITELIST_I_TO_US:
        return s[:-1] + 'us'
    # -ae -> -a (casiae -> cassia)
    if s.endswith('ae') and ' ' not in s:
        return s[:-2] + 'a'
    # -is (gen.) some neuters -> try -e/-um only via whitelist
    if s == 'mellis':
        return 'mel'
    if s == 'vini':
        return 'vinum'
    # Default: unchanged
    return s


def lemmatize(label: str, language: str, overrides: Dict[str, str]) -> str:
    if not label:
        return ''
    # Overrides first
    if label in overrides:
        return overrides[label]
    lang = (language or '').lower()
    try:
        if lang.startswith('gr'):
            return _lemmatize_greek(label)
        if lang.startswith('la'):
            return _lemmatize_latin(label)
    except Exception:
        pass
    return label

