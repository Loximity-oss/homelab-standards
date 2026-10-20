# Child-token policy for the adguard app plays (token role apps-adguard). Create only, never update: create-only is
# enforced by OpenBao. Explicit zones with an adguard deployment (wifi, iot); a new zone = Class C change here.
path "wifi/secret/data/apps/adguard" { capabilities = ["create"] }
path "wifi/secret/data/apps/adguard/*" { capabilities = ["create"] }
path "iot/secret/data/apps/adguard" { capabilities = ["create"] }
path "iot/secret/data/apps/adguard/*" { capabilities = ["create"] }
