from __future__ import annotations

from difflib import get_close_matches

SYNONYM_GROUPS = (
    ("电脑", "笔记本", "计算机"),
    ("书", "教材"),
    ("灯", "台灯", "照明"),
    ("单车", "自行车"),
    ("手机", "电话"),
)

_SYNONYM_MAP = {}
for _group in SYNONYM_GROUPS:
    for _word in _group:
        _SYNONYM_MAP.setdefault(_word, set()).update(_group)

_TOKEN_WEIGHTS = (
    ("name", 3),
    ("category", 2),
    ("description", 1),
    ("seller", 1),
)


def _text(value):
    return str(value or "").lower()


def _tokens(query):
    return [token for token in _text(query).split() if token]


def _variants(token):
    return _SYNONYM_MAP.get(token, {token}) | {token}


def _score_item(item, tokens):
    fields = {field: _text(item.get(field, "")) for field, _ in _TOKEN_WEIGHTS}
    combined = " ".join(fields.values())
    score = 0
    for token in tokens:
        variants = _variants(token)
        if not any(variant in combined for variant in variants):
            return None
        for field, weight in _TOKEN_WEIGHTS:
            if any(variant in fields[field] for variant in variants):
                score += weight
    return score


def search_items(items, query):
    """Filter with AND semantics across whitespace-separated tokens.

    Matching is case-insensitive across name, category, description and seller.
    Results are sorted by relevance (name 3, category 2, description/seller 1),
    then by descending id. An empty query returns the input order unchanged.
    """
    tokens = _tokens(query)
    if not tokens:
        return list(items)

    scored = []
    for item in items:
        score = _score_item(item, tokens)
        if score is not None:
            scored.append((score, int(item.get("id") or 0), item))

    scored.sort(key=lambda entry: (-entry[0], -entry[1]))
    return [item for _, _, item in scored]


def suggest_similar_items(items, query, limit=3):
    """Return up to limit close product names for a no-result query."""
    query = str(query or "").strip()
    if not query:
        return []

    names = []
    for item in items:
        name = item.get("name", "") if isinstance(item, dict) else item
        name = str(name or "").strip()
        if name and name not in names:
            names.append(name)

    return get_close_matches(query, names, n=limit, cutoff=0.4)


def sort_items(items, sort_option):
    """Apply the price sorts; other values keep the incoming order."""
    result = list(items)
    if sort_option == "价格从低到高":
        result.sort(key=lambda item: (float(item["price"]), -int(item.get("id") or 0)))
    elif sort_option == "价格从高到低":
        result.sort(key=lambda item: (-float(item["price"]), -int(item.get("id") or 0)))
    return result
