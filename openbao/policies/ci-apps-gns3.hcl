# Child-token policy for the gns3 app plays (token role apps-gns3): admin-credential escrow, create only, stg only.
path "stg/secret/data/apps/gns3" { capabilities = ["create"] }
path "stg/secret/data/apps/gns3/*" { capabilities = ["create"] }
