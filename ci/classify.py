#!/usr/bin/env python3
"""Classify a homelab-standards PR. Usage: classify.py <base_dir> <head_dir> <name-status file> [author]
B: only additions (new keys / list items) to naming/roles.yaml, naming/services.yaml, naming/tags.yaml.
C: anything else (zones, IP bands, VMID blocks, protected.yaml, secrets.yaml, openbao/, lint/, ci/, .gitea/, docs).
Owner rule (v7, decisions 3/13): every changed file must be owned by the PR author in main's owners.yaml
(faris may change anything); otherwise "owner_violations" is non-empty and the check fails."""
import fnmatch, json, pathlib, sys, yaml
base, head, changes = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), open(sys.argv[3]).read().split("\n")
author = sys.argv[4] if len(sys.argv) > 4 else ""
B_FILES = {"naming/roles.yaml", "naming/services.yaml", "naming/tags.yaml"}
owners = list(((yaml.safe_load((base / "owners.yaml").read_text()) or {}).get("owners") or {}).items()) \
    if (base / "owners.yaml").exists() else []


def owner_of(path):
    return next((list(o) for g, o in owners if fnmatch.fnmatch(path, g)), ["faris"])


def additions_only(old, new):
    if isinstance(old, dict) and isinstance(new, dict):
        return all(k in new and additions_only(v, new[k]) for k, v in old.items())
    if isinstance(old, list) and isinstance(new, list):
        return all(x in new for x in old)
    return old == new


reasons_b, reasons_c, violations = [], [], []
for line in filter(None, changes):
    status, *paths = line.split("\t")
    for p in paths:
        if author and author != "faris" and author not in owner_of(p):
            violations.append(f"{p} (owner: {', '.join(owner_of(p))})")
    path = paths[-1]
    if status[0] != "M" or path not in B_FILES:
        reasons_c.append(f"{status[0]} {path}")
        continue
    old, new = yaml.safe_load((base / path).read_text()), yaml.safe_load((head / path).read_text())
    ok = additions_only(old, new)
    (reasons_b if ok else reasons_c).append(f"{'additions to' if ok else 'changes/removals in'} {path}")
cls = "C" if reasons_c or not reasons_b else "B"
print(json.dumps({"class": cls, "reasons": (reasons_c or reasons_b) or ["no changes"], "owner_violations": sorted(set(violations))}))
