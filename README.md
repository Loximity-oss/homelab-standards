# homelab-standards

This repo holds the rules that the machines enforce for site `hm1`: naming rules, controlled vocabularies, hard limits, and OpenBao policies as code. It does not hold guests, applications, or agent code.

## Status

- State: live.
- Checked: 2026-11-02.
- Used by: the PR gates of `homelab-infra` and `homelab-apps`, Terraform, and the OpenClaw agents.
- A merge to `main` takes effect at the next pipeline run. The agents refresh their clone within 15 minutes.

## Place in the system

| Repo | Owns | Reads from this repo |
|---|---|---|
| `homelab-infra` | Guests, base OS, pipeline | `naming/zones.yaml`, `protected.yaml`, `lint/naming.py` |
| `homelab-apps` | Application catalogue and deployments | Naming rules, `protected.yaml`, `lint/naming.py` |
| **`homelab-standards`** (this repo) | Rules and hard limits | — |
| `openclaw` | The AIOps agent team | A read-only clone, including `owners.yaml` |

## Layout

| Path | Content |
|---|---|
| `naming-conventions.md` | The naming conventions |
| `readme-standard.md` | The README rule |
| `naming/sites.yaml` | Site codes |
| `naming/zones.yaml` | For each zone: VLAN, subnet, gateway, pool, VMID block, IP bands |
| `naming/roles.yaml` | Role codes for host names |
| `naming/services.yaml` | Service DNS names |
| `naming/tags.yaml` | Proxmox tag vocabulary |
| `naming/vmid-ranges.yaml` | VMID ranges outside the zones |
| `naming/secrets.yaml` | OpenBao path, key, and AppRole naming rules |
| `protected.yaml` | Protected guests, templates, bridges, and subnets |
| `proxmox-acls.yaml` | Proxmox roles and permissions |
| `flows.yaml` | Allowed traffic between zones, with the UniFi state of each flow |
| `owners.yaml` | The owner of each file |
| `openbao/` | OpenBao policies and AppRoles as code. See `openbao/README.md` |
| `lint/naming.py` | The checker for the PR gate |
| `ci/` | PR checks, the classifier, and the apply scripts |
| `.gitea/workflows/` | `pr.yml` and `apply.yml` |

## Change process

- Nobody pushes to `main`. Every change is a PR.
- Branch: `<type>/<issue#>-<slug>`. Title: `type(scope): text`. Start the title with `WIP: ` for a plan without a merge.
- `ci/classify.py` computes the class from the saved PR head. It does not read the label.

| Class | Change | Approval |
|---|---|---|
| B | Additions to `naming/roles.yaml`, `naming/services.yaml`, or `naming/tags.yaml` | `oc-rev` approves |
| C | Every other change | Faris approves |

- Only the merge broker (`ci-merger`) or Faris merges a PR.
- The PR check runs `lint/naming.py` from `main` on the data of the PR. The code of the PR never runs.
- After a merge, `apply` pushes the registered tags and pools to Proxmox.

## Write access

`owners.yaml` sets the owner of each file. The first matching pattern wins. A file that is not listed belongs to `faris`.

| Owner | Files |
|---|---|
| `faris` | `protected.yaml`, `owners.yaml`, `openbao/`, `.gitea/`, `naming/sites.yaml`, and every file not listed |
| `oc-net` | `naming/zones.yaml`, `flows.yaml` |
| `oc-infra` | `naming/vmid-ranges.yaml`, `naming/roles.yaml`, `naming/tags.yaml`, `naming/services.yaml`, `naming/secrets.yaml`, `lint/`, `ci/` |
| `oc-infra`, `oc-net` | `naming-conventions.md`, `README.md` |

The CI check fails a PR when its author does not own a changed file. `faris` can change any file.

## Key concepts

- **Zone:** a network segment. `naming/zones.yaml` gives each zone its VLAN, subnet, gateway, pool, VMID block, and IP bands.
- **Protected:** `protected.yaml` lists the guests, templates, bridges, and subnets that agents and the pipeline never change.
- **Vocabulary:** roles, services, tags, and secret names are fixed lists. A host name must use these lists.
- **Flow:** an entry in `flows.yaml`. It names the source, the destination, the ports, and the state (`proposed` or `implemented`). Do not rely on a `proposed` flow.
- **Owner:** the person or agent that can change a file.
- **OpenBao as code:** the file name of a policy in `openbao/policies/` is the policy name.

## Local checks

Check the names of a change:

```
python3 lint/naming.py --infra <homelab-infra checkout> [--branch B] [--title T]
```

Use `--repo apps` and `--apps <homelab-apps checkout>` to check `homelab-apps`.

Compute the class of a change:

```
python3 ci/classify.py <base_dir> <head_dir> <name-status file> [author]
```

The output is JSON. It gives `class`, `reasons`, and `owner_violations`.

## Operations

- `pr.yml` runs on the runner `host-plan` for every PR event.
- `apply.yml` runs on the runner `host-apply` after a merge to `main`.
- `openbao/check.py` runs every night on `hm1-shr-aiops01`. It reads the OpenBao policies and AppRoles. It opens a `platform` issue in `homelab/openclaw` when they differ from this repo.

## Secrets and safety

This repo holds no secret value. It holds names, paths, and policies only.

- Caution: `protected.yaml` and `proxmox-acls.yaml` set the hard limits of the site. A wrong change can give an agent access to a protected guest or to `vmbr0`. Faris approves these changes.
- Caution: the pipeline never applies `openbao/`. Faris runs `openbao/apply.sh`. Run it with `--dry-run` first.
- Caution: only root applies `proxmox-acls.yaml`. Apply it again after you destroy or restore a guest.

## Documents

| Document | Topic |
|---|---|
| `naming-conventions.md` | The naming conventions |
| `readme-standard.md` | The README rule and the term list |
| `openbao/README.md` | Apply, drift check, and secret rotation for OpenBao |

## Known gaps

- The status table at the top of `naming-conventions.md` is out of date.
- The design of DNS for the internal zones (`tru`, `int`, `dmz`, `stg`) is not decided.
- Some entries in `flows.yaml` have the state `proposed`. The network does not confirm them yet.
- The Proxmox role `DevOpsAdmin` has `Mapping.*` and `Sys.Modify` on `/`. Reduce them before you add a guest with PCI passthrough.
