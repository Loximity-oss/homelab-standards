path "secret/data/hm1/platform/aiops" { capabilities = ["read"] }
path "secret/data/inbox/*" { capabilities = ["create"] }
# zone namespaces: key names only (never values); app secrets create-only (no update = never overwritten)
path "+/secret/metadata" { capabilities = ["list"] }
path "+/secret/metadata/*" { capabilities = ["list"] }
path "+/secret/data/apps/*" { capabilities = ["create"] }
# drift check (openclaw-nightly-scan): read policy text, AppRole settings and namespaces, never secrets or secret IDs
path "sys/policies/acl" { capabilities = ["list"] }
path "sys/policies/acl/*" { capabilities = ["read"] }
path "auth/approle/role" { capabilities = ["list"] }
path "auth/approle/role/+" { capabilities = ["read"] }
path "sys/namespaces" { capabilities = ["list"] }
