#!/usr/bin/env python3
"""Compare live OpenBao policies and AppRole settings with openbao/ in homelab-standards (read-only).
Usage: check.py <standards_dir>   (needs BAO_ADDR, BAO_CACERT, BAO_TOKEN with the aiops policy)
Prints differences one per line; exit 1 if any."""
import ipaddress, json, os, sys, urllib.request, ssl, yaml, pathlib
S = pathlib.Path(sys.argv[1]) / "openbao"
ctx = ssl.create_default_context(cafile=os.environ["BAO_CACERT"])
def get(path, method="GET"):
    req = urllib.request.Request(f"{os.environ['BAO_ADDR']}/v1/{path}", method=method, headers={"X-Vault-Token": os.environ["BAO_TOKEN"]})
    try:
        return json.load(urllib.request.urlopen(req, context=ctx, timeout=15))
    except urllib.error.HTTPError as e:
        return None if e.code == 404 else sys.exit(f"openbao {path}: {e.code}")
diffs = []
live = set(get("sys/policies/acl?list=true")["data"]["keys"]) - {"root", "default"}
want = {p.stem for p in (S / "policies").glob("*.hcl")}
for n in sorted(live - want): diffs.append(f"policy {n}: exists in OpenBao but not in Git")
for n in sorted(want - live): diffs.append(f"policy {n}: in Git but not in OpenBao")
for n in sorted(want & live):
    if get(f"sys/policies/acl/{n}")["data"]["policy"].strip() != (S / "policies" / f"{n}.hcl").read_text().strip():
        diffs.append(f"policy {n}: text differs from Git")
c = yaml.safe_load(open(S / "approles.yaml")); d = c["defaults"]
live_roles = set((get("auth/approle/role?list=true") or {"data": {"keys": []}})["data"]["keys"])
for n in sorted(live_roles - set(c["approles"])): diffs.append(f"approle {n}: exists in OpenBao but not in Git")
for n, r in c["approles"].items():
    x = get(f"auth/approle/role/{n}")
    if not x: diffs.append(f"approle {n}: missing in OpenBao"); continue
    x = x["data"]
    def nets(v): return sorted(str(ipaddress.ip_network(x, strict=False)) for x in (v or []))
    def secs(v): return int(v[:-1]) * {"s": 1, "m": 60, "h": 3600}[v[-1]] if isinstance(v, str) else int(v)
    checks = {"token_policies": (sorted(x.get("token_policies") or []), sorted(r["policies"])),
              "token_ttl": (x.get("token_ttl"), secs(d["token_ttl"])), "token_max_ttl": (x.get("token_max_ttl"), secs(d["token_max_ttl"])),
              "secret_id_bound_cidrs": (nets(x.get("secret_id_bound_cidrs")), nets(r["cidrs"])),
              "token_bound_cidrs": (nets(x.get("token_bound_cidrs")), nets(r["cidrs"]))}
    for k, (have, wantv) in checks.items():
        if have != wantv: diffs.append(f"approle {n}: {k} is {have}, Git says {wantv}")
print("\n".join(diffs) or "openbao: in sync with Git")
sys.exit(1 if diffs else 0)
