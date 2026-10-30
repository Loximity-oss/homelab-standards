#!/usr/bin/env python3
"""Naming / hard-limit checker for homelab-infra and homelab-apps. Owned by homelab-standards (changes are Class C).

Usage: naming.py [--repo infra] --infra PATH [--branch NAME] [--title TITLE] [--standards PATH]
       naming.py --repo apps --apps PATH [--branch NAME] [--title TITLE] [--standards PATH]
Exit 0 = clean, 1 = violations (printed one per line as `path: message`).
"""
import argparse, ipaddress, pathlib, re, sys
import yaml

REPOS = ("infra", "apps")
REQUIRED = {"hostname", "vmid", "type", "role", "os", "ip", "owner", "patch"}
SIZING = {"cores", "memory_mb", "disk_gb"}          # required for lxc; optional for vm (baseline 2/2048/16, decision 32 D6)
OPTIONAL = SIZING | {"datastore", "description", "swap_mb", "nesting", "env", "keyctl", "tests", "extra_nics", "cpu_type"}
LXC_ONLY = {"swap_mb", "nesting", "keyctl"}
VM_ONLY = {"tests", "extra_nics", "cpu_type"}
NO_OS = "none"                                     # os: none = VM with a blank disk, no OS since day 0 (Faris 2026-10-31)
TEST_EXEMPTIONS = {"l1-only"}                      # allowed ONLY with os: none (L2/L3 can't run without an OS)
CPU_TYPES = {"x86-64-v2-AES", "host"}              # vm cpu_type; host = nested virtualisation (lab VMs)
MAX_EXTRA_NICS = 15                                # net1-net15; net0 is always the zone NIC
TYPES = {"lxc", "vm"}
DATASTORES = {"lvmt-nvme01", "lvmt-sata01"}
VM_MIN_DISK_GB = 8                                 # template 9000 disk


def os_family(os_code):  # tests/os/<family>.* in homelab-infra (decision 32: no OS deploys without its baseline tests)
    return "ubuntu" if os_code.startswith("ubuntu") else "debian" if os_code.startswith("debian") else "windows" if os_code.startswith("win") else os_code
BRANCH_RE = re.compile(r"^(feat|fix|chore|patch|app|net|learn|docs)/([0-9]+-)?[a-z0-9][a-z0-9-]*$")
TITLE_RE = re.compile(r"^(WIP:? )?(feat|fix|chore|patch|app|net|learn|docs)(\([a-z0-9-]+\))?!?: \S")
SECRET_REF_RE = re.compile(r"""\bsecret/(?:data/)?([a-z0-9][a-z0-9/_-]*[a-z0-9])""")

# homelab-apps (naming-conventions.md 8.6)
APP_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
APP_NAME_MAX = 30
APP_EXAMPLES = {"_example"}                        # status `example`: catalogue only, never deployed
APP_PLACEHOLDERS = {".gitkeep"}                    # keeps empty folders (e.g. deployments/stg/) in Git
APPS_TITLE_RE = re.compile(r"^(WIP:? )?(feat|fix|chore|patch|app|net|learn|docs)(\((?:_example|[a-z0-9-]+)\))?!?: \S")


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


def app_name_problem(name, allow_example=True):
    """The catalogue entry name rule (homelab-apps). Returns '' when valid, else the reason."""
    if allow_example and name in APP_EXAMPLES:
        return ""
    if len(name) > APP_NAME_MAX:
        return f"app name '{name}' is {len(name)} chars (max {APP_NAME_MAX})"
    if not APP_NAME_RE.match(name):
        return f"app name '{name}' must be lowercase a-z 0-9, words joined by single '-', starting with a letter"
    return ""


def lint_infra(a, S, I, zones_doc, roles, err):
    site, zones = zones_doc["site"], zones_doc["zones"]
    role_codes = set(roles["roles"]) - set(roles.get("network_device_roles", []))
    tags = load(S / "naming/tags.yaml")["keys"]
    prot = load(S / "protected.yaml")
    prot_vmids = {int(v) for v in prot.get("vmids", {})}
    prot_bridges = set(prot.get("bridges", []))
    tpl_lo, tpl_hi = prot.get("templates", [9000, 9199])
    prot_nets = [ipaddress.ip_network(n) for n in prot.get("subnets", [])]

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
        if s.get("type") != "vm" and VM_ONLY & set(s):
            err(rel, f"{sorted(VM_ONLY & set(s))} are vm-only")
        if s.get("type") == "vm":
            if LXC_ONLY & set(s):
                err(rel, f"{sorted(LXC_ONLY & set(s))} are lxc-only")
            if isinstance(s.get("disk_gb"), int) and s["disk_gb"] < VM_MIN_DISK_GB:
                err(rel, f"disk_gb must be >= {VM_MIN_DISK_GB} for a vm (template disk)")
        if s.get("os") == NO_OS:
            if s.get("type") != "vm":
                err(rel, "os 'none' is only for type vm (blank disk, no template)")
            if s.get("tests") != "l1-only":
                err(rel, "os 'none' needs tests: l1-only (no OS: L2/L3 can't run)")
        elif "tests" in s:
            err(rel, "tests: l1-only is only allowed with os: none (guests with an OS are always tested L1-L3)")
        if "tests" in s and s["tests"] not in TEST_EXEMPTIONS:
            err(rel, f"tests must be one of {sorted(TEST_EXEMPTIONS)}")
        if "cpu_type" in s and s["cpu_type"] not in CPU_TYPES:
            err(rel, f"cpu_type must be one of {sorted(CPU_TYPES)}")
        if isinstance(s.get("os"), str) and s["os"] != NO_OS:
            fam = os_family(s["os"])
            if not list((pathlib.Path(a.infra) / "tests" / "os").glob(f"{fam}.*")):
                err(rel, f"os '{s['os']}' has no baseline tests (homelab-infra tests/os/{fam}.*): add them first")
        if "datastore" in s and s["datastore"] not in DATASTORES:
            err(rel, f"datastore must be one of {sorted(DATASTORES)}")
        z = zones.get(zone)
        if not z:
            err(rel, f"stack directory '{zone}' is not a zone code"); continue
        if not z.get("guests"):
            err(rel, f"zone '{zone}' does not take pipeline guests")
        if z.get("bridge") in prot_bridges:
            err(rel, f"zone '{zone}' uses protected bridge {z.get('bridge')}")
        if "extra_nics" in s:
            nics, lab = s["extra_nics"], z.get("lab_bridges") or []
            if not isinstance(nics, list) or not nics or not all(isinstance(b, str) for b in nics):
                err(rel, "extra_nics must be a non-empty list of bridge names")
            else:
                if len(nics) > MAX_EXTRA_NICS:
                    err(rel, f"extra_nics: at most {MAX_EXTRA_NICS} (net1-net{MAX_EXTRA_NICS})")
                if len(set(nics)) != len(nics):
                    err(rel, "extra_nics lists a bridge twice")
                for b in nics:
                    if b in prot_bridges:
                        err(rel, f"extra_nics: {b} is a protected bridge")
                    elif b not in lab:
                        err(rel, f"extra_nics: {b} is not a lab bridge of zone '{zone}' (naming/zones.yaml lab_bridges: {lab}; Network Engineer)")

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


def lint_apps(A, zones_doc, roles, err):
    """homelab-apps: catalogue entry folder = entry name, deployment path = deployments/<zone>/<app>.yaml.
    Everything beyond naming (specs, pattern counts, waves, pins, secret path shape) is apps scripts/catalog.py."""
    zones = zones_doc["zones"]
    role_codes = set(roles["roles"]) - set(roles.get("network_device_roles", []))

    entries = set()
    cat = A / "catalog"
    if cat.is_dir():
        for d in sorted(cat.iterdir()):
            rel = d.relative_to(A)
            if d.name in APP_PLACEHOLDERS:
                continue
            if d.is_symlink() or not d.is_dir():
                err(rel, "catalog/ holds only entry folders catalog/<app>/ (no files, no symlinks)"); continue
            why = app_name_problem(d.name)
            if why:
                err(rel, why)
            entries.add(d.name)
            f = d / "app.yaml"
            frel = f.relative_to(A)
            if f.is_symlink() or not f.is_file():
                err(rel, "entry has no app.yaml (catalog/<app>/app.yaml)"); continue
            try:
                e = load(f)
            except Exception as x:
                err(frel, f"invalid YAML: {x}"); continue
            if not isinstance(e, dict):
                err(frel, "app.yaml must be a mapping"); continue
            if e.get("name") != d.name:
                err(frel, f"name '{e.get('name')}' must equal the entry folder '{d.name}'")
            c = e.get("catalog")
            r = c.get("role") if isinstance(c, dict) else None
            if r is None:
                continue
            codes = [r] if isinstance(r, str) else r if isinstance(r, list) else None
            if codes is None:
                err(frel, "catalog.role must be a role code or a list of role codes"); continue
            for code in codes:
                if code not in role_codes:
                    err(frel, f"catalog.role '{code}' not in naming/roles.yaml (owner: oc-infra; open a standards PR)")

    dep = A / "deployments"
    if dep.is_dir():
        for zd in sorted(dep.iterdir()):
            rel = zd.relative_to(A)
            if zd.name in APP_PLACEHOLDERS:
                continue
            if zd.is_symlink() or not zd.is_dir():
                err(rel, "deployments/ holds only zone folders: deployments/<zone>/<app>.yaml"); continue
            zone = zd.name
            zv = zones.get(zone)
            if not zv:
                err(rel, f"'{zone}' is not a zone code in naming/zones.yaml {sorted(zones)}")
            elif not zv.get("guests"):
                err(rel, f"zone '{zone}' does not take guests (naming/zones.yaml)")
            for f in sorted(zd.iterdir()):
                frel = f.relative_to(A)
                if f.name in APP_PLACEHOLDERS:
                    continue
                if f.is_symlink() or not f.is_file() or f.suffix != ".yaml":
                    err(frel, "must be deployments/<zone>/<app>.yaml (a regular file with suffix .yaml)"); continue
                app = f.stem
                why = app_name_problem(app, allow_example=False)
                if why:
                    err(frel, why)
                elif app not in entries:
                    err(frel, f"no catalogue entry catalog/{app}/ for this deployment")
                try:
                    d = load(f)
                except Exception as x:
                    err(frel, f"invalid YAML: {x}"); continue
                if not isinstance(d, dict):
                    err(frel, "deployment must be a mapping"); continue
                if d.get("app") != app:
                    err(frel, f"app '{d.get('app')}' must equal the file name '{app}'")
                if d.get("zone") != zone:
                    err(frel, f"zone '{d.get('zone')}' must equal the folder '{zone}'")
                hosts = d.get("hosts")
                if hosts is None:
                    continue
                if not isinstance(hosts, list):
                    err(frel, "hosts must be a list of hostnames"); continue
                for h in hosts:
                    ok, why, m = parse_hostname(str(h), zones_doc, roles)
                    if not ok:
                        err(frel, why)
                    elif m["zone"] != zone:
                        err(frel, f"host '{h}' is in zone '{m['zone']}', not '{zone}'")


def lint_secrets(S, R, err):
    sec = load(S / "naming/secrets.yaml") if (S / "naming/secrets.yaml").exists() else None
    if (R / "secrets").exists() or list(R.rglob("*.sops.yaml")):
        err("secrets", "no secrets in Git: secrets live in OpenBao (naming/secrets.yaml)")
    if sec:
        path_re = re.compile(sec["path_pattern"])
        for f in R.rglob("*"):
            if not f.is_file() or ".git" in f.parts or f.suffix not in {".yml", ".yaml", ".j2", ".tf", ".hcl", ".tpl", ".sh", ".py", ".md"}:
                continue
            try:
                txt = f.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for m in SECRET_REF_RE.finditer(txt):
                ref = m.group(1)
                if ref.startswith(("hm1/", "inbox/")) and not path_re.match(ref):
                    err(f.relative_to(R), f"OpenBao path 'secret/{ref}' does not match naming/secrets.yaml path_pattern")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", choices=REPOS, default="infra")
    ap.add_argument("--infra")
    ap.add_argument("--apps")
    ap.add_argument("--standards", default=str(pathlib.Path(__file__).resolve().parents[1]))
    ap.add_argument("--branch")
    ap.add_argument("--title")
    a = ap.parse_args()
    if a.repo == "infra" and not a.infra:
        ap.error("--infra PATH is required with --repo infra")
    if a.repo == "apps" and not a.apps:
        ap.error("--apps PATH is required with --repo apps")
    S = pathlib.Path(a.standards)
    R = pathlib.Path(a.infra if a.repo == "infra" else a.apps)

    zones_doc = load(S / "naming/zones.yaml")
    roles = load(S / "naming/roles.yaml")

    errs = []
    def err(path, msg):
        errs.append(f"{path}: {msg}")

    if a.repo == "infra":
        lint_infra(a, S, R, zones_doc, roles, err)
        title_re, title_eg = TITLE_RE, "'feat(shr): add dns01'"
    else:
        lint_apps(R, zones_doc, roles, err)
        title_re, title_eg = APPS_TITLE_RE, "'app(adguard): bump to v0.107.80'"
    lint_secrets(S, R, err)

    if a.branch and not BRANCH_RE.match(a.branch):
        err("branch", f"'{a.branch}' must be <type>/<issue#>-<slug>, type in feat|fix|chore|patch|app|net|learn|docs")
    if a.title and not title_re.match(a.title):
        err("title", f"'{a.title}' must be a Conventional Commit, e.g. {title_eg} (prefix 'WIP: ' to hold)")

    for e in errs:
        print(e)
    print(f"naming: {len(errs)} violation(s)", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
