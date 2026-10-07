#!/usr/bin/env bash
# Apply openbao/ to OpenBao. Run by Faris with an admin token (never by the pipeline):
#   export BAO_ADDR=https://192.168.70.12:8200 BAO_CACERT=<ca.crt>; bao login -method=userpass username=faris
#   ./openbao/apply.sh            # add --dry-run to only show differences
set -euo pipefail
cd "$(dirname "$0")"
DRY=${1:-}
# zone namespaces (or fallback mounts) with KV v2 at secret/
MODE=$(python3 -c 'import yaml;print(yaml.safe_load(open("namespaces.yaml"))["mode"])')
for ns in $(python3 -c 'import yaml;print(" ".join(yaml.safe_load(open("namespaces.yaml"))["namespaces"]))'); do
  if [ "$MODE" = namespace ]; then
    bao namespace list -format=json 2>/dev/null | jq -e --arg n "$ns/" 'index($n)' >/dev/null && echo "namespace $ns: exists" || {
      echo "namespace $ns: missing"; [ "$DRY" = --dry-run ] || bao namespace create "$ns" >/dev/null; }
    BAO_NAMESPACE=$ns bao secrets list -format=json 2>/dev/null | jq -e '."secret/"' >/dev/null || {
      echo "namespace $ns: kv secret/ missing"; [ "$DRY" = --dry-run ] || BAO_NAMESPACE=$ns bao secrets enable -path=secret -version=2 kv >/dev/null; }
  else
    bao secrets list -format=json | jq -e --arg m "secret-$ns/" '.[$m]' >/dev/null && echo "mount secret-$ns: exists" || {
      echo "mount secret-$ns: missing"; [ "$DRY" = --dry-run ] || bao secrets enable -path=secret-$ns -version=2 kv >/dev/null; }
  fi
done
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
