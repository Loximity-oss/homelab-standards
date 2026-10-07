# OpenBao as code

- `policies/*.hcl` — every ACL policy (file name = policy name). `approles.yaml` — every AppRole (name = policy name, bound CIDRs, TTLs) and the userpass admin.
- **Apply (Faris only):** log in as `faris`, then `./openbao/apply.sh --dry-run` and `./openbao/apply.sh`. The pipeline never applies this.
- **Drift:** CT 100 runs `check.py` nightly with the `aiops` token (read-only on policies/roles) and opens a `platform` issue in `homelab/openclaw` on differences.
- **Rotate a secret_id:** `bao write -f -field=secret_id auth/approle/role/<role>/secret-id` → replace `/etc/openbao/<role>/secret_id` on the client.
- Not covered here (set once at build): KV mount `secret/`, audit device (declared in `openbao.hcl`), snapshot token, unseal shares.
