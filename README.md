# homelab-standards

Source of truth for naming conventions, controlled vocabularies and hard limits.

- **Write access: Faris only.** Agents and CI read it.
- Need a new value (role code, service name, tag, secret path)? Agents use `report_issue(kind="standards")`; it opens a `proposal` issue here and links the blocked work.
- Consumers: `homelab-infra` PR gate runs `lint/naming.py`; Terraform reads `naming/zones.yaml` and `protected.yaml`; OpenClaw agents read a local clone.

| Path | What |
|---|---|
| `naming-conventions.md` | The conventions |
| `naming/sites.yaml` | Site codes |
| `naming/zones.yaml` | Zone code ↔ VLAN ↔ subnet ↔ gateway ↔ pool ↔ VMID block ↔ IP bands |
| `naming/roles.yaml` | Role codes for hostnames |
| `naming/services.yaml` | Service DNS names |
| `naming/tags.yaml` | Proxmox tag vocabulary (mirrors the host's registered tags) |
| `naming/vmid-ranges.yaml` | Non-zone VMID ranges (templates, temporary) |
| `naming/secrets.yaml` | OpenBao path, key and AppRole naming; secrets rules |
| `openbao/` | OpenBao policies (`policies/*.hcl`) and AppRoles (`approles.yaml`) as code; `apply.sh` (Faris only), `check.py` (drift) |
| `protected.yaml` | Hard limits: protected VMIDs, bridges, subnets |
| `lint/naming.py` | Checker: `python3 lint/naming.py --infra <homelab-infra checkout> [--branch B] [--title T]` |
