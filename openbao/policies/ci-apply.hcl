path "secret/data/hm1/platform/ci/plan" { capabilities = ["read"] }
path "secret/data/hm1/platform/ci/apply" { capabilities = ["read"] }
# provisioning secrets: written once per guest by Ansible on the apply runner, never read back
path "+/secret/data/guests/*" { capabilities = ["create"] }
