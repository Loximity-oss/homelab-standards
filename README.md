# homelab-standards

Source of truth for naming conventions, controlled vocabularies and hard limits.

- **Managed through the pipeline:** agents (Infrastructure Engineer) open PRs; nobody pushes to `main`.
  - **Class B** (Reviewer `oc-rev` approves and merges): only additions to `naming/roles.yaml`, `naming/services.yaml`, `naming/tags.yaml`.
  - **Class C** (Faris): everything else — patterns, zones/IP plan, VMID blocks, `protected.yaml`, `naming/secrets.yaml`, `openbao/`, `lint/`, `ci/`, `.gitea/`, the conventions doc.
  - PR checks run **main's** `lint/naming.py` against the PR's data and homelab-infra `main`; PR code never runs.
  - After a merge, `apply` pushes registered tags and pools to Proxmox. OpenBao policies (`openbao/`) are still applied by Faris.
- Need a new value? The Infrastructure Engineer opens a PR here (usually Class B).
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
| `ci/`, `.gitea/workflows/` | PR checks + classification (`ci-pr.sh`, `classify.py`), apply to Proxmox (`ci-apply.sh`, `apply-proxmox.py`) |
| `lint/naming.py` | Checker: `python3 lint/naming.py --infra <homelab-infra checkout> [--branch B] [--title T]` |
