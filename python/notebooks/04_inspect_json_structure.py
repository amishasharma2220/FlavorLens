"""
Phase 1c — Raw JSON structure inspection
-------------------------------------------
This version of the Zomato dataset ships as raw API JSON dumps (file1.json
through file5.json) rather than a flat CSV. Before writing any parsing
code, we need to see the actual nested structure — Zomato's API JSON
schema isn't guaranteed to match any particular blog post's description
of it.

Usage:
    python python/notebooks/04_inspect_json_structure.py
"""

import json

JSON_PATH = "python/data/raw/archive/file1.json"  # adjust to your actual path


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 60)
    print(f"TOP-LEVEL TYPE: {type(data)}")
    print("=" * 60)

    if isinstance(data, list):
        print(f"Top-level list length: {len(data)}")
        first_entry = data[0]
    elif isinstance(data, dict):
        print(f"Top-level dict keys: {list(data.keys())}")
        # Common Zomato dump shape: {"restaurants": [...]}
        first_key = list(data.keys())[0]
        first_entry = data[first_key][0] if isinstance(data[first_key], list) else data[first_key]
    else:
        print("Unexpected top-level type — inspect manually.")
        return

    print("\n" + "=" * 60)
    print("FIRST ENTRY — FULL STRUCTURE (pretty-printed)")
    print("=" * 60)
    print(json.dumps(first_entry, indent=2)[:4000])  # cap output length

    # Try to find the actual restaurant list, however it's nested
    print("\n" + "=" * 60)
    print("SEARCHING FOR NESTED 'restaurant' OR 'restaurants' KEYS")
    print("=" * 60)

    def find_keys(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if "restaurant" in k.lower():
                    print(f"Found key: {new_path} (type: {type(v)})")
                find_keys(v, new_path)
        elif isinstance(obj, list) and obj:
            find_keys(obj[0], f"{path}[0]")

    find_keys(first_entry)


if __name__ == "__main__":
    main()