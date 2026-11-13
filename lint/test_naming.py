#!/usr/bin/env python3
"""Tests for the named single-guest exception in lint/naming.py (zone guest_allow + protected.yaml exemptions).
Offline: builds temporary standards/infra trees and runs naming.py. Run: python3 lint/test_naming.py"""
import copy, pathlib, subprocess, sys, tempfile, unittest
import yaml

NAMING = pathlib.Path(__file__).resolve().parent / "naming.py"

ZONES = {"site": "hm1", "domain": "lox-internal.dev", "zones": {
    "mgt": {"vlan": 2, "cidr": "192.168.67.0/28", "gateway": "192.168.67.1", "bridge": "vmbr0", "guests": False,
            "vmid": [100, 199], "reserved_ips": {"192.168.67.2": "hm1-mgt-pve01"},
            "guest_allow": {"hm1-mgt-jump01": {"vmid": 110, "ip": "192.168.67.10", "bridge": "vmbr0", "type": "vm"}}},
    "stg": {"vlan": 60, "cidr": "192.168.76.0/24", "gateway": "192.168.76.1", "bridge": "vmbr1", "guests": True,
            "vmid": [800, 899], "ip_bands": {"static": [10, 99]}}}}
PROTECTED = {"vmids": {300: "hm1-shr-cicd01"}, "templates": [9000, 9199], "bridges": ["vmbr0"],
             "subnets": ["192.168.67.0/28", "192.168.70.13/32"],
             "exemptions": {"hm1-mgt-jump01": {"vmid": 110, "ip": "192.168.67.10/32", "bridge": "vmbr0", "type": "vm",
                                               "reason": "mgt jumpbox"}}}
ROLES = {"roles": {"jump": "Jump", "tst": "Test", "gw": "Gateway"}, "network_device_roles": ["gw"]}
TAGS = {"keys": {"zone": ["mgt", "stg"], "os": ["ubuntu2604", "none"], "owner": ["infra"], "patch": ["ring1"],
                 "env": ["prod", "staging"]}}
JUMP = {"hostname": "hm1-mgt-jump01", "vmid": 110, "type": "vm", "role": "jump", "os": "ubuntu2604",
        "ip": "192.168.67.10", "owner": "infra", "patch": "ring1", "cores": 2, "memory_mb": 2048}
TST = {"hostname": "hm1-stg-tst01", "vmid": 810, "type": "lxc", "role": "tst", "os": "ubuntu2604",
       "ip": "192.168.76.20", "owner": "infra", "patch": "ring1", "cores": 1, "memory_mb": 1024, "disk_gb": 8}


def run(zones=None, prot=None, specs=None, ns=("mgt", "stg")):
    zones = copy.deepcopy(ZONES if zones is None else zones)
    prot = copy.deepcopy(PROTECTED if prot is None else prot)
    specs = [("mgt", JUMP), ("stg", TST)] if specs is None else specs
    with tempfile.TemporaryDirectory() as d:
        S, I = pathlib.Path(d, "standards"), pathlib.Path(d, "infra")
        for p, doc in {"naming/zones.yaml": zones, "naming/roles.yaml": ROLES, "naming/tags.yaml": TAGS,
                       "protected.yaml": prot, "openbao/namespaces.yaml": {"namespaces": list(ns)},
                       "openbao/pki.yaml": {"roles": {z: {} for z in ns}}}.items():
            (S / p).parent.mkdir(parents=True, exist_ok=True)
            (S / p).write_text(yaml.safe_dump(doc))
        (I / "tests/os").mkdir(parents=True)
        (I / "tests/os/ubuntu.yaml").write_text("{}\n")
        for zone, spec in specs:
            g = I / "terraform/stacks/hm1" / zone / "guests"
            g.mkdir(parents=True, exist_ok=True)
            (g / f"{spec['hostname']}.yaml").write_text(yaml.safe_dump(spec))
        r = subprocess.run([sys.executable, str(NAMING), "--standards", str(S), "--infra", str(I)],
                           capture_output=True, text=True)
        return r.returncode, r.stdout


def spec(**kw):
    s = dict(JUMP); s.update(kw)
    return [("mgt", s), ("stg", TST)]


class Exception_(unittest.TestCase):
    def fails(self, *needles, **kw):
        rc, out = run(**kw)
        self.assertEqual(rc, 1, out)
        for n in needles:
            self.assertIn(n, out)
        return out

    def test_exact_match_passes(self):
        rc, out = run()
        self.assertEqual(rc, 0, out)

    def test_regular_guest_zone_unaffected(self):
        z = copy.deepcopy(ZONES); del z["zones"]["mgt"]["guest_allow"]
        p = copy.deepcopy(PROTECTED); del p["exemptions"]
        rc, out = run(zones=z, prot=p, specs=[("stg", TST)])
        self.assertEqual(rc, 0, out)

    def test_without_exemption_fails(self):
        p = copy.deepcopy(PROTECTED); del p["exemptions"]
        self.fails("does not take pipeline guests", "protected bridge vmbr0", "is in a protected subnet",
                   "no matching protected.yaml exemptions.hm1-mgt-jump01", prot=p)

    def test_without_guest_allow_fails(self):
        z = copy.deepcopy(ZONES); del z["zones"]["mgt"]["guest_allow"]
        self.fails("does not take pipeline guests", "protected bridge vmbr0", "is in a protected subnet", zones=z)

    def test_spec_vmid_mismatch_fails(self):
        self.fails("exception not granted: spec vmid 111", "does not take pipeline guests", specs=spec(vmid=111))

    def test_spec_ip_mismatch_fails(self):
        self.fails("exception not granted: spec ip 192.168.67.11", "is in a protected subnet",
                   specs=spec(ip="192.168.67.11"))

    def test_other_hostname_fails(self):
        self.fails("does not take pipeline guests", "protected bridge vmbr0",
                   specs=spec(hostname="hm1-mgt-jump02"))

    def test_second_guest_in_mgt_fails(self):
        other = dict(JUMP, hostname="hm1-mgt-jump02", vmid=111, ip="192.168.67.11")
        out = self.fails("hm1-mgt-jump02.yaml: zone 'mgt' does not take pipeline guests",
                         specs=[("mgt", JUMP), ("mgt", other)])
        self.assertNotIn("hm1-mgt-jump01.yaml", out)

    def test_exemption_bridge_mismatch_fails(self):
        p = copy.deepcopy(PROTECTED); p["exemptions"]["hm1-mgt-jump01"]["bridge"] = "vmbr1"
        self.fails("bridge vmbr0 (guest_allow) != vmbr1 (protected.yaml)", "protected bridge vmbr0", prot=p)

    def test_exemption_wide_prefix_fails(self):
        p = copy.deepcopy(PROTECTED); p["exemptions"]["hm1-mgt-jump01"]["ip"] = "192.168.67.0/28"
        self.fails("must be one host address", "is in a protected subnet", prot=p)

    def test_exemption_unknown_key_fails(self):
        p = copy.deepcopy(PROTECTED); p["exemptions"]["hm1-mgt-jump01"]["extra_nics"] = ["vmbr0"]
        self.fails("unknown keys ['extra_nics']", prot=p)

    def test_extra_nics_on_exempt_fails(self):
        z = copy.deepcopy(ZONES); z["zones"]["mgt"]["lab_bridges"] = ["vmbr10"]
        self.fails("no extra_nics", "does not take pipeline guests", zones=z, specs=spec(extra_nics=["vmbr10"]))

    def test_type_mismatch_fails(self):
        self.fails("spec type lxc != pinned type vm", specs=spec(type="lxc", disk_gb=8))

    def test_guest_allow_in_guest_zone_fails(self):
        z = copy.deepcopy(ZONES)
        z["zones"]["stg"]["guest_allow"] = {"hm1-stg-tst01": {"vmid": 810, "ip": "192.168.76.20", "bridge": "vmbr1"}}
        self.fails("stg.guest_allow is only for zones with guests: false", zones=z)

    def test_missing_namespace_fails(self):
        self.fails("guest zone mgt has no OpenBao namespace", "guest zone mgt has no PKI role", ns=("stg",))


if __name__ == "__main__":
    unittest.main()
