#!/usr/bin/env python3
"""Make Proxmox match homelab-standards: registered tags (exact set from naming/tags.yaml) and pools (created
from naming/zones.yaml; never deleted automatically). Uses the apply token (DevOpsAdmin) from PVE_TOKEN."""
import json, os, ssl, sys, urllib.parse, urllib.request, yaml
S = sys.argv[1]
API = "https://192.168.67.2:8006/api2/json"
H = {"Authorization": f"PVEAPIToken={os.environ['PVE_TOKEN']}"}
ctx = ssl._create_unverified_context()
def call(method, path, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(API + path, data=body, method=method, headers=H)
    return json.load(urllib.request.urlopen(req, context=ctx, timeout=30)).get("data")
tags = yaml.safe_load(open(f"{S}/naming/tags.yaml"))
want = sorted({f"{k}-{v}" for k, vals in tags["keys"].items() for v in vals} | set(tags.get("flags", [])))
have = sorted(call("GET", "/cluster/options").get("registered-tags") or [])
if want != have:
    call("PUT", "/cluster/options", {"registered-tags": ";".join(want)})
    print(f"registered tags: +{sorted(set(want) - set(have))} -{sorted(set(have) - set(want))}")
else:
    print(f"registered tags: in sync ({len(want)})")
zones = yaml.safe_load(open(f"{S}/naming/zones.yaml"))["zones"]
pools = {p["poolid"] for p in call("GET", "/pools")}
for z, c in zones.items():
    if c.get("pool") and c["pool"] not in pools:
        lo, hi = c.get("vmid", ["?", "?"])
        call("POST", "/pools", {"poolid": c["pool"], "comment": f"Zone {z} (VLAN {c.get('vlan')}), VMIDs {lo}-{hi}"})
        print(f"pool {c['pool']}: created")
print(f"pools: {len([z for z in zones.values() if z.get('pool')])} declared, none deleted automatically")
