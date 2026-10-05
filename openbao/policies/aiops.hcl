path "secret/data/hm1/platform/aiops" { capabilities = ["read"] }
path "secret/data/inbox/*" { capabilities = ["create","update"] }
# drift check (openclaw-policy-check): read policy text and AppRole settings, never secrets or secret IDs
path "sys/policies/acl" { capabilities = ["list"] }
path "sys/policies/acl/*" { capabilities = ["read"] }
path "auth/approle/role" { capabilities = ["list"] }
path "auth/approle/role/+" { capabilities = ["read"] }
