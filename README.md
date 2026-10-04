# homelab-standards

Source of truth for naming conventions, controlled vocabularies and hard limits.

- **Write access: Faris only.** Agents and CI read it.
- Need a new value (role code, service name, tag)? Open an issue here with the value and why, and link the blocked PR.
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
| `protected.yaml` | Hard limits: protected VMIDs, bridges, subnets |
| `lint/naming.py` | Checker: `python3 lint/naming.py --infra <homelab-infra checkout> [--branch B] [--title T]` |
