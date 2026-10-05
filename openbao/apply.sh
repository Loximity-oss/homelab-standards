#!/usr/bin/env bash
# Apply openbao/ to OpenBao. Run by Faris with an admin token (never by the pipeline):
#   export BAO_ADDR=https://192.168.70.12:8200 BAO_CACERT=<ca.crt>; bao login -method=userpass username=faris
#   ./openbao/apply.sh            # add --dry-run to only show differences
set -euo pipefail
cd "$(dirname "$0")"
DRY=${1:-}
for f in policies/*.hcl; do
  n=$(basename "$f" .hcl)
  if diff -q <(bao policy read "$n" 2>/dev/null) "$f" >/dev/null 2>&1; then echo "policy $n: in sync"; continue; fi
  echo "policy $n: differs"; [ "$DRY" = --dry-run ] || bao policy write "$n" "$f" >/dev/null
done
python3 - "$DRY" <<'PY'
import json, subprocess, sys, yaml
dry = sys.argv[1] == "--dry-run"
c = yaml.safe_load(open("approles.yaml")); d = c["defaults"]
for name, r in c["approles"].items():
    want = {"token_policies": r["policies"], "token_ttl": d["token_ttl"], "token_max_ttl": d["token_max_ttl"],
            "secret_id_ttl": d["secret_id_ttl"], "secret_id_bound_cidrs": r["cidrs"], "token_bound_cidrs": r["cidrs"]}
    args = [f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in want.items()]
    print(f"approle {name}: {'would write' if dry else 'write'} {' '.join(args)}")
    if not dry:
        subprocess.run(["bao", "write", f"auth/approle/role/{name}", *args], check=True, stdout=subprocess.DEVNULL)
PY
