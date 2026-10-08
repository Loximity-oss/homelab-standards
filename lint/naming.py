#!/usr/bin/env python3
"""Naming / hard-limit checker for homelab-infra. Owned by homelab-standards (Faris-only).

Usage: naming.py --infra PATH [--branch NAME] [--title TITLE] [--standards PATH]
Exit 0 = clean, 1 = violations (printed one per line as `path: message`).
"""
import argparse, ipaddress, pathlib, re, sys
import yaml

REQUIRED = {"hostname", "vmid", "type", "role", "os", "ip", "owner", "patch"}
SIZING = {"cores", "memory_mb", "disk_gb"}          # required for lxc; optional for vm (baseline 2/2048/16, decision 32 D6)
OPTIONAL = SIZING | {"datastore", "description", "swap_mb", "nesting", "env", "keyctl"}
LXC_ONLY = {"swap_mb", "nesting", "keyctl"}
TYPES = {"lxc", "vm"}
DATASTORES = {"lvmt-nvme01", "lvmt-sata01"}
VM_MIN_DISK_GB = 8                                 # template 9000 disk
BRANCH_RE = re.compile(r"^(feat|fix|chore|patch|app|net|learn|docs)/([0-9]+-)?[a-z0-9][a-z0-9-]*$")
TITLE_RE = re.compile(r"^(WIP:? )?(feat|fix|chore|patch|app|net|learn|docs)(\([a-z0-9-]+\))?!?: \S")
SECRET_REF_RE = re.compile(r"""\bsecret/(?:data/)?([a-z0-9][a-z0-9/_-]*[a-z0-9])""")


def load(p):
    with open(p) as f:
        return yaml.safe_load(f) or {}


def parse_hostname(h, zones_doc, roles_doc):
    """The single hostname rule (imported by OpenClaw's propose_guest and homelab-infra scripts).
    Returns (ok, reason, parts). Pattern: <site>-<zone>-<role><nn>, zone 3-4 letters, max 15 chars (NetBIOS)."""
    site, zones = zones_doc["site"], zones_doc["zones"]
    roles = set(roles_doc["roles"]) - set(roles_doc.get("network_device_roles", []))
    m = re.fullmatch(rf"{site}-(?P<zone>[a-z]{{3,4}})-(?P<role>[a-z][a-z0-9]{{1,4}})(?P<nn>[0-9]{{2}})", h or "")
    if len(h or "") > 15:
        return False, f"hostname '{h}' is {len(h)} chars (max 15, NetBIOS)", {}
    if not m:
        return False, f"hostname '{h}' does not match {site}-<zone>-<role><nn> (zone 3-4 letters)", {}
    if m["zone"] not in zones:
        return False, f"zone '{m['zone']}' is not in naming/zones.yaml {sorted(zones)}", {}
    if m["role"] not in roles:
        return False, f"role '{m['role']}' not in naming/roles.yaml (owner: oc-infra; open a standards PR)", {}
    return True, "", m.groupdict()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infra", required=True)
    ap.add_argument("--standards", default=str(pathlib.Path(__file__).resolve().parents[1]))
    ap.add_argument("--branch")
    ap.add_argument("--title")
    a = ap.parse_args()
    S, I = pathlib.Path(a.standards), pathlib.Path(a.infra)

    zones_doc = load(S / "naming/zones.yaml")
    site, zones = zones_doc["site"], zones_doc["zones"]
    roles = load(S / "naming/roles.yaml")
    role_codes = set(roles["roles"]) - set(roles.get("network_device_roles", []))
    tags = load(S / "naming/tags.yaml")["keys"]
    prot = load(S / "protected.yaml")
    prot_vmids = {int(v) for v in prot.get("vmids", {})}
    prot_bridges = set(prot.get("bridges", []))
    tpl_lo, tpl_hi = prot.get("templates", [9000, 9199])
    prot_nets = [ipaddress.ip_network(n) for n in prot.get("subnets", [])]

    errs = []
    def err(path, msg):
        errs.append(f"{path}: {msg}")

    # v7.1: every guest zone needs an OpenBao namespace (one-time guest secrets) and a PKI role (ACME)
    ob = S / "openbao"
    if (ob / "namespaces.yaml").exists():
        nss = set(load(ob / "namespaces.yaml").get("namespaces", []))
        pki_roles = set((load(ob / "pki.yaml").get("roles") or {})) if (ob / "pki.yaml").exists() else set()
        for zc, zv in zones.items():
            if zv.get("guests"):
                if zc not in nss:
                    err("openbao/namespaces.yaml", f"guest zone {zc} has no OpenBao namespace")
                if zc not in pki_roles:
                    err("openbao/pki.yaml", f"guest zone {zc} has no PKI role")

    seen = {"hostname": {}, "vmid": {}, "ip": {}}

    stacks = I / "terraform/stacks" / site
    for spec_path in sorted(stacks.glob("*/guests/*.yaml")):
        rel = spec_path.relative_to(I)
        zone = spec_path.parent.parent.name
        try:
            s = load(spec_path)
        except Exception as e:
            err(rel, f"invalid YAML: {e}"); continue
        if not isinstance(s, dict):
            err(rel, "spec must be a mapping"); continue
        missing, unknown = REQUIRED - set(s), set(s) - REQUIRED - OPTIONAL
        if missing: err(rel, f"missing keys: {sorted(missing)}")
        if unknown: err(rel, f"unknown keys: {sorted(unknown)}")
        if s.get("type") == "lxc" and SIZING - set(s):
            err(rel, f"lxc needs {sorted(SIZING - set(s))}")
        if s.get("type") == "vm":
            if LXC_ONLY & set(s):
                err(rel, f"{sorted(LXC_ONLY & set(s))} are lxc-only")
            if isinstance(s.get("disk_gb"), int) and s["disk_gb"] < VM_MIN_DISK_GB:
                err(rel, f"disk_gb must be >= {VM_MIN_DISK_GB} for a vm (template disk)")
        if "datastore" in s and s["datastore"] not in DATASTORES:
            err(rel, f"datastore must be one of {sorted(DATASTORES)}")
        z = zones.get(zone)
        if not z:
            err(rel, f"stack directory '{zone}' is not a zone code"); continue
        if not z.get("guests"):
            err(rel, f"zone '{zone}' does not take pipeline guests")
        if z.get("bridge") in prot_bridges:
            err(rel, f"zone '{zone}' uses protected bridge {z.get('bridge')}")

        h = str(s.get("hostname", ""))
        if spec_path.stem != h:
            err(rel, f"file name must be '<hostname>.yaml' (hostname is '{h}')")
        ok, why, m = parse_hostname(h, zones_doc, roles)
        if not ok:
            err(rel, why)
        else:
            if m["zone"] != zone:
                err(rel, f"hostname zone '{m['zone']}' != stack zone '{zone}'")
            if m["role"] != s.get("role"):
                err(rel, f"hostname role '{m['role']}' != spec role '{s.get('role')}'")
        if s.get("role") not in role_codes:
            err(rel, f"role '{s.get('role')}' not in naming/roles.yaml (open an issue in homelab-standards)")
        if s.get("type") not in TYPES:
            err(rel, f"type must be one of {sorted(TYPES)}")

        vmid = s.get("vmid")
        if not isinstance(vmid, int):
            err(rel, "vmid must be an integer")
        else:
            lo, hi = z.get("vmid", [0, -1])
            if not lo <= vmid <= hi:
                err(rel, f"vmid {vmid} outside zone '{zone}' block {lo}-{hi}")
            if vmid in prot_vmids:
                err(rel, f"vmid {vmid} is protected (protected.yaml)")
            if tpl_lo <= vmid <= tpl_hi:
                err(rel, f"vmid {vmid} is in the template range {tpl_lo}-{tpl_hi} (protected.yaml); templates are never managed")

        try:
            ip = ipaddress.ip_address(str(s.get("ip")))
            net = ipaddress.ip_network(z["cidr"])
            if ip not in net:
                err(rel, f"ip {ip} not in zone '{zone}' subnet {net}")
            last = int(str(ip).split(".")[-1])
            bands = z.get("ip_bands", {})
            if not any(b[0] <= last <= b[1] for b in bands.values()):
                err(rel, f"ip {ip} not in an allowed band for '{zone}': {bands}")
            if any(ip in n for n in prot_nets):
                err(rel, f"ip {ip} is in a protected subnet")
            if str(ip) in (z.get("reserved_ips") or {}):
                err(rel, f"ip {ip} is reserved for {z['reserved_ips'][str(ip)]}")
        except (ValueError, KeyError) as e:
            err(rel, f"ip invalid: {e}")

        for key in ("os", "owner", "patch", "env"):
            if key in s and s[key] not in tags.get(key, []):
                err(rel, f"{key} '{s[key]}' not in naming/tags.yaml {tags.get(key)}")
        if "keyctl" in s and not isinstance(s["keyctl"], bool):
            err(rel, "keyctl must be true or false")
        for key in ("cores", "memory_mb", "disk_gb"):
            if key in s and (not isinstance(s[key], int) or s[key] <= 0):
                err(rel, f"{key} must be a positive integer")

        for key in ("hostname", "vmid", "ip"):
            v = s.get(key)
            if v is None: continue
            if v in seen[key]:
                err(rel, f"duplicate {key} '{v}' (also in {seen[key][v]})")
            seen[key][v] = rel

    sec = load(S / "naming/secrets.yaml") if (S / "naming/secrets.yaml").exists() else None
    if (I / "secrets").exists() or list(I.rglob("*.sops.yaml")):
        err("secrets", "no secrets in Git: secrets live in OpenBao (naming/secrets.yaml)")
    if sec:
        path_re = re.compile(sec["path_pattern"])
        for f in I.rglob("*"):
            if not f.is_file() or ".git" in f.parts or f.suffix not in {".yml", ".yaml", ".j2", ".tf", ".hcl", ".tpl", ".sh", ".py", ".md"}:
                continue
            try:
                txt = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for m in SECRET_REF_RE.finditer(txt):
                ref = m.group(1)
                if ref.startswith(("hm1/", "inbox/")) and not path_re.match(ref):
                    err(f.relative_to(I), f"OpenBao path 'secret/{ref}' does not match naming/secrets.yaml path_pattern")

    if a.branch and not BRANCH_RE.match(a.branch):
        err("branch", f"'{a.branch}' must be <type>/<issue#>-<slug>, type in feat|fix|chore|patch|app|net|learn|docs")
    if a.title and not TITLE_RE.match(a.title):
        err("title", f"'{a.title}' must be a Conventional Commit, e.g. 'feat(shr): add dns01' (prefix 'WIP: ' to hold)")

    for e in errs:
        print(e)
    print(f"naming: {len(errs)} violation(s)", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
