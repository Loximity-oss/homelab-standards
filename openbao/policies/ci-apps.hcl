# homelab-apps pipeline (AppRole ci-apps, runner-apps on CT 300). Proposal infra docs/proposals/homelab-apps 5b, agreed #125.
# Reads only its own CI secrets and may mint per-app child tokens; it has no secret-create path itself.
path "secret/data/hm1/platform/ci/apps" { capabilities = ["read"] }
path "auth/token/create/apps-*" { capabilities = ["update"] }
