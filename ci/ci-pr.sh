#!/usr/bin/env bash
# Standards PR: main's lint on the PR's data + infra main, yamllint, gitleaks, classify (B = additions to
# roles/services/tags only; everything else C), label, request review. No Class A here.
# Output: /var/lib/devops/plans/std-<HEAD_SHA>/class.json, written only when every check and the owner rule passed.
# The merge broker (homelab-infra host/merge-broker, infra #135) merges on it; no file = no merge.
BASE=$(cd "$(dirname "$0")/.." && pwd); WORK=$(dirname "$BASE")
source "$BASE/ci/lib.sh"
bao_login ci-plan; export GITEA_API_TOKEN UNIFI_CI_USER UNIFI_CI_PASS; GITEA_API_TOKEN=$(secret plan gitea_ci_token)
UNIFI_CI_USER=$(secret plan unifi_ci_user 2>/dev/null || true); UNIFI_CI_PASS=$(secret plan unifi_ci_pass 2>/dev/null || true); bao_logout
git -C "$BASE" fetch -q origin "refs/pull/$PR/head"
[ "$(git -C "$BASE" rev-parse FETCH_HEAD)" = "$HEAD_SHA" ] || { echo "PR head moved"; exit 0; }
PLANS=/var/lib/devops/plans
find "$PLANS" -mindepth 1 -maxdepth 1 -type d -name 'std-*' -mtime +14 -exec rm -rf {} + 2>/dev/null || true
OUT="$PLANS/std-$HEAD_SHA"; rm -rf "$OUT"   # a failed re-run of this head must not leave an older class behind
HEAD_DIR="$WORK/head"; rm -rf "$HEAD_DIR"; git -C "$BASE" worktree add -q -f --detach "$HEAD_DIR" "$HEAD_SHA"
MAIN=$(git -C "$BASE" rev-parse origin/main)
if ! git -C "$BASE" merge-base --is-ancestor "$MAIN" "$HEAD_SHA"; then
  python3 "$BASE/ci/gitea.py" update-branch "$PR"; echo "Branch was behind main; updated it. A new run follows." > "$WORK/c.md"
  python3 "$BASE/ci/gitea.py" comment "$PR" "$WORK/c.md"; exit 0
fi
INFRA="$WORK/infra"; rm -rf "$INFRA"; clone homelab/homelab-infra "$INFRA" "$GITEA_API_TOKEN"
R="$WORK/report.md"; : > "$R"; fail=0
chk() { local n=$1; shift; if "$@" > "$WORK/$n.log" 2>&1; then echo "- ✅ $n" >> "$R"; else fail=1; { echo "- ❌ **$n**"; echo '```'; head -40 "$WORK/$n.log"; echo '```'; } >> "$R"; fi; }
chk "naming lint (main's checker, PR data, infra main)" python3 "$BASE/lint/naming.py" --standards "$HEAD_DIR" --infra "$INFRA"
chk yamllint yamllint -d relaxed "$HEAD_DIR"
chk gitleaks gitleaks dir "$HEAD_DIR" --no-banner --redact
if git -C "$BASE" diff --name-only "$MAIN...$HEAD_SHA" | grep -qx 'naming/zones.yaml'; then
  urc=0; python3 "$BASE/ci/check-unifi.py" "$HEAD_DIR" > "$WORK/unifi.log" 2>&1 || urc=$?
  case $urc in
    0) echo "- ✅ zones match UniFi (read-only)" >> "$R" ;;
    2) echo "- ⚠️ zones vs UniFi: **skipped** — $(tail -1 "$WORK/unifi.log")" >> "$R" ;;
    *) fail=1; { echo "- ❌ **zones match UniFi (read-only)**"; echo '```'; head -40 "$WORK/unifi.log"; echo '```'; } >> "$R" ;;
  esac
fi
if [ $fail -ne 0 ]; then { echo "## ❌ Checks failed"; echo; cat "$R"; } > "$WORK/c.md"; python3 "$BASE/ci/gitea.py" comment "$PR" "$WORK/c.md"; exit 1; fi
git -C "$BASE" diff --name-status "$MAIN...$HEAD_SHA" > "$WORK/changed.txt"
python3 "$BASE/ci/classify.py" "$BASE" "$HEAD_DIR" "$WORK/changed.txt" "${AUTHOR:-}" > "$WORK/class.json"
OWN=$(python3 -c 'import json,sys;print("; ".join(json.load(open(sys.argv[1]))["owner_violations"]))' "$WORK/class.json")
if [ -n "$OWN" ]; then
  printf '## ❌ Owner rule

`%s` does not own: %s

Only the owning engineer (owners.yaml) or faris may change these files. Ask the PM to route it.
' "$AUTHOR" "$OWN" > "$WORK/c.md"
  python3 "$BASE/ci/gitea.py" comment "$PR" "$WORK/c.md"; exit 1
fi
CLASS=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["class"])' "$WORK/class.json")
install -d -m 0750 "$OUT"; install -m 0640 "$WORK/class.json" "$OUT/class.json"
WIP=""; case "$TITLE" in WIP*) WIP=wip;; esac
python3 "$BASE/ci/gitea.py" labels "$PR" "class/$CLASS${WIP:+,wip}"
case "$CLASS$WIP" in
  B) G="Class B — additions to vocabularies only; needs the Reviewer (\`oc-rev\`)."; python3 "$BASE/ci/gitea.py" review-request "$PR" oc-rev || true ;;
  C) G="Class C — changes rules, patterns, hard limits, OpenBao policies or the pipeline; needs Faris."; python3 "$BASE/ci/gitea.py" review-request "$PR" faris || true ;;
  *wip) G="WIP — checked only; remove WIP from the title to request review." ;;
esac
python3 - "$WORK/class.json" "$R" "$G" > "$WORK/c.md" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
print(f"## Class {c['class']}\n\n{sys.argv[3]}\n\n**Why:** " + "; ".join(c["reasons"][:10]) + "\n\n### Checks\n" + open(sys.argv[2]).read())
PY
python3 "$BASE/ci/gitea.py" comment "$PR" "$WORK/c.md"
