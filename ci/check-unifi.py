#!/usr/bin/env python3
"""Read-only: every zone in naming/zones.yaml must match its UniFi network (VLAN, subnet, gateway). design-v7 decision 7.
Usage: check-unifi.py <standards_dir>   env: UNIFI_CI_USER, UNIFI_CI_PASS (read-only UniFi local user), UNIFI_HOST.
Exit 0 = match, 1 = mismatch, 2 = skipped (no UniFi CI credential; shown as ⚠️, does not fail the PR)."""
import ipaddress, json, os, ssl, sys, urllib.request, http.cookiejar, yaml

S = sys.argv[1]
HOST = os.environ.get("UNIFI_HOST", "192.168.68.1")
user, pw = os.environ.get("UNIFI_CI_USER"), os.environ.get("UNIFI_CI_PASS")
zones = yaml.safe_load(open(f"{S}/naming/zones.yaml"))["zones"]
if not user or not pw:
    print("skipped: no UniFi CI credential in OpenBao (secret/hm1/platform/ci/plan unifi_ci_user/unifi_ci_pass)")
    sys.exit(2)
ctx = ssl._create_unverified_context()   # UDM self-signed; read-only call
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), urllib.request.HTTPCookieProcessor(jar))
req = urllib.request.Request(f"https://{HOST}/api/auth/login", data=json.dumps({"username": user, "password": pw}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
resp = op.open(req, timeout=20)
csrf = resp.headers.get("X-CSRF-Token") or resp.headers.get("x-csrf-token") or ""
nets = json.load(op.open(urllib.request.Request(f"https://{HOST}/proxy/network/api/s/default/rest/networkconf",
                                                 headers={"X-CSRF-Token": csrf}), timeout=20))["data"]
by_vlan = {}
for n in nets:
    if not n.get("ip_subnet"):
        continue
    vlan = int(n["vlan"]) if n.get("vlan_enabled") and n.get("vlan") else 1
    by_vlan.setdefault(vlan, []).append(n)
errs = []
for z, c in zones.items():
    cands = by_vlan.get(int(c["vlan"]), [])
    if not cands:
        errs.append(f"{z}: VLAN {c['vlan']} does not exist in UniFi")
        continue
    n = cands[0] if len(cands) == 1 else next((x for x in cands if x.get("name") == c.get("name")), cands[0])
    iface = ipaddress.ip_interface(n["ip_subnet"])
    if str(iface.network) != str(ipaddress.ip_network(c["cidr"])):
        errs.append(f"{z}: cidr {c['cidr']} but UniFi '{n.get('name')}' VLAN {c['vlan']} is {iface.network}")
    if c.get("gateway") and str(iface.ip) != c["gateway"]:
        errs.append(f"{z}: gateway {c['gateway']} but UniFi says {iface.ip}")
print("\n".join(errs) or f"zones match UniFi ({len(zones)} zones)")
sys.exit(1 if errs else 0)
