path "secret/data/hm1/platform/ci/plan" { capabilities = ["read"] }
path "secret/data/hm1/platform/ci/apply" { capabilities = ["read"] }
# provisioning secrets: written once per guest by Ansible on the apply runner, never read back
path "+/secret/data/guests/*" { capabilities = ["create"] }
# app secrets generated at deploy (create-only, never read back): AdGuard admin password per DNS guest (infra #45)
path "+/secret/data/apps/adguard/*" { capabilities = ["create"] }
