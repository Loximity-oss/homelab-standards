#!/usr/bin/env bash
# After a merge to main: push standards to Proxmox (registered tags from naming/tags.yaml, pools from naming/zones.yaml).
BASE=$(cd "$(dirname "$0")/.." && pwd)
source "$BASE/ci/lib.sh"
bao_login ci-apply; export GITEA_API_TOKEN PVE_TOKEN
GITEA_API_TOKEN=$(secret plan gitea_ci_token); PVE_TOKEN=$(secret apply pve_token_apply); bao_logout
OUT=$(mktemp -d); set +e
python3 "$BASE/ci/apply-proxmox.py" "$BASE" > "$OUT/apply.log" 2>&1; rc=$?; set -e
read -r PR _ <<<"$(python3 "$BASE/ci/gitea.py" pr-of-commit "$SHA")" || true
{ [ $rc -eq 0 ] && echo "## Apply (\`${SHA:0:8}\`) ✅" || echo "## Apply (\`${SHA:0:8}\`) ❌"; echo; echo '```'; cat "$OUT/apply.log"; echo '```'; } > "$OUT/c.md"
[ -n "${PR:-}" ] && python3 "$BASE/ci/gitea.py" comment "$PR" "$OUT/c.md"
cat "$OUT/apply.log"; exit $rc
