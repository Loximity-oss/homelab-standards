# Child-token policy for the k3s app plays (token role apps-k3s): join-token escrow, create only, shr only.
path "shr/secret/data/apps/k3s" { capabilities = ["create"] }
path "shr/secret/data/apps/k3s/*" { capabilities = ["create"] }
