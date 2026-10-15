# Template workflow (homelab-infra #53): runner host-template on CT 300 reads only its own CI secret
# (pve_token_template, gitea_ci_token). No guest, app or other CI paths.
path "secret/data/hm1/platform/ci/template" { capabilities = ["read"] }
