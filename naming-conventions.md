# Naming Conventions

| | |
|---|---|
| **Status** | Design, written 2026-10-03, for the Proxmox rebuild ("nuke and redo"). Nothing is renamed yet |
| **Applies to** | Everything rebuilt on PRX-SRV001: guests, network, DNS, Proxmox objects, identities, IaC, Git, secrets, ops artefacts. This includes guests not managed by DevOps |
| **Decided** | Keep current UniFi addressing (§3.1) · site code in names · internal domain `lox-internal.dev`, public `loximity.dev` · hostnames ≤ 15 chars (NetBIOS, AD later) · conventions live in the `homelab-standards` repo, writable by Faris only (§1); engineers are stewards |
| **Open** | §0 site code value |
| **Related** | `architecture-network.md`, `architecture-proxmox.md`, `architecture-devops.md`, `architecture-aiops.md` |

---

## 0. Principles and decisions

1. **One name, one meaning.** A name says *where* (site, zone), *what* (role) and *which one* (number). Owner, OS, size and IP are not in names. They change, so they live in tags, inventory and IPAM.
2. **Hostname ≠ service name.** Hosts get numbered names (`hm1-shr-dns01`). Clients use service names (`dns.lox-internal.dev`, `git.lox-internal.dev`). Moving a service means changing one CNAME.
3. **Lowest common denominator.** Hostnames are lowercase `a-z 0-9 -`, start with a letter, ≤ 15 chars, so the same string works as a Linux hostname, DNS label, Proxmox guest name, Terraform key and future AD computer name (AD displays it upper-case. That's fine).
4. **Controlled vocabularies.** Every code (site, zone, role, service, tag) comes from a YAML list in `homelab-standards` (`naming/*.yaml`). Only Faris edits them. An agent that needs a new code opens an issue (§10).
5. **Enforced, not remembered.** `lint/naming.py` from `homelab-standards` runs in the `homelab-infra` PR gate and fails the PR on any violation (§11).

**Site code: `hm1`** (proposed, "home site 1"). It is a placeholder: changing it before the rebuild is a one-word find-and-replace. The external site reached by site-to-site VPN gets the next code (`ex1` or similar) when it is first managed. Site codes are always 3 chars: 2 letters + 1 digit.

---

## 1. Source of truth and ownership

### 1.1 The `homelab-standards` repo

The conventions live in their own Gitea repo, `homelab/homelab-standards`, separate from `homelab-infra`. Only Faris can change it. Agents and pipelines read it.

```
homelab-standards/
├── naming-conventions.md        # this document
├── naming/
│   ├── sites.yaml
│   ├── zones.yaml               # zone code ↔ VLAN ↔ subnet ↔ router (§3.1)
│   ├── roles.yaml               # §2.3
│   ├── services.yaml            # §4
│   ├── tags.yaml                # §6.5
│   └── vmid-ranges.yaml         # §5
├── protected.yaml               # hard limits: protected VMIDs, vmbr0, management subnet
└── lint/
    └── naming.py                # the checker run by every consuming repo
```

| Who | Access |
|---|---|
| `faris` | Write. Only account in the `main` push whitelist; force-push off |
| `oc-*` agents, `ci-merger`, `ci-runner` | Read (can open issues) |
| `devops-admin` | Break-glass only |

Why a separate repo: write access in `homelab-infra` is shared by every agent and the merge bot, so an agent PR could otherwise change a name *and* the rule that checks it. Keeping the vocabularies, the hard-limit list and the checker itself here means no agent can widen what is allowed, including the protected guests.

How it is consumed:
- **Pipeline:** `homelab-infra`'s `pr.yml` checks out `homelab-standards` (read-only token, `main`) and runs `lint/naming.py` and the `protected.yaml` check before plan. A violation fails the PR before the Reviewer sees it.
- **Hard limits:** the Terraform guard, `classify.py`, the MCP tools and the Proxmox ACL sync read `protected.yaml` instead of hard-coding VMIDs.
- **Agents (CT 106/100):** a read-only clone at `/opt/openclaw/standards`, refreshed every 15 min by a timer. The `naming` skill points to the YAML files rather than the full doc, which keeps token use low.
- **Version:** consumers follow `main`, so an edit takes effect on the next PR run. For a breaking rename, change the YAML and the affected code together, or tag a release and pin to it for the transition.

### 1.2 Stewards

Engineers don't edit conventions. Each is the **steward** of its area: it knows the rules, applies them, notices gaps and proposes changes as issues. Every change is Faris's, so change classes don't apply to the conventions themselves.

| # | Convention | Steward (8-agent team) |
|---|---|---|
| 2 | Hostnames and role codes | Infrastructure Engineer (app role codes: Application Engineer) |
| 3 | Sites, zones, VLANs, IP plan | Network Engineer |
| 4 | DNS and service names | Network Engineer (app service names: Application Engineer) |
| 5 | VMIDs | Infrastructure Engineer |
| 6 | Proxmox objects (storage, bridges, pools, tags) | Infrastructure Engineer (bridges: Network Engineer) |
| 7 | Identities (users, service accounts, tokens, groups) | Infrastructure Engineer (platform) · Systems Engineer (OS-local) |
| 8.1 | Terraform | Infrastructure Engineer |
| 8.2 | Ansible (OS roles, groups) | Systems Engineer |
| 8.3 | Ansible app roles, app config | Application Engineer |
| 8.4 | Git (branches, commits, labels, tags) | Infrastructure Engineer |
| 8.5 | Secrets (SOPS files and keys) | Infrastructure Engineer |
| 9.1 | Alerts, runbooks, dashboards | SRE |
| 9.2 | Snapshots, backups | SRE |
| 9.3 | Patch artefacts | Systems Engineer |
| 9.4 | Learning artefacts | Tutor |

The Reviewer checks that PRs follow the conventions beyond what the linter can catch, e.g. a role code that is valid but the wrong one.

---

## 2. Hostnames (guests and physical hosts)

### 2.1 Pattern

```
<site>-<zone>-<role><nn>
 hm1  - shr  - dns  01      →  hm1-shr-dns01   (13 chars)
```

| Part | Length | Rule |
|---|---|---|
| `site` | 3 | §0 (`hm1`) |
| `zone` | 3 | §3.1 zone code: where the primary NIC lives |
| `role` | 2–5 | Role code from `naming/roles.yaml` (§2.3) |
| `nn` | 2 | `01`–`99`, never reused within site+zone+role while the old one exists |

Maximum = 3 + 1 + 3 + 1 + 5 + 2 = **15**, the NetBIOS limit, by construction. Clusters with distinct node types put the type in the role code (`k3sc`, `k3sw`) rather than adding a segment.

Rules:
- Lowercase only. No `_`, no dots, no OS or size words (`ubuntu`, `big`), no person names, no `test` (use the `lab` zone instead).
- The Proxmox guest name, OS hostname, DNS A record, Terraform key and Ansible inventory name are **the same string**.
- Multi-homed guests are named after the zone of their primary (default-route) NIC.
- Templates are not hosts: they use §6.4.

### 2.2 Examples (target inventory after the rebuild)

| Today | New name | Len |
|---|---|---|
| PRX-SRV001 (PVE host) | `hm1-mgt-pve01` | 13 |
| AISVC-CNT001 (CT 106, OpenClaw) | `hm1-mgt-aiops01` | 15 |
| DEVOPS-CNT001 (CT 107, Gitea + runner) | `hm1-shr-cicd01` | 14 |
| DNSSVC-CNT001/002 | `hm1-shr-dns01`, `hm1-shr-dns02` | 13 |
| GUAC (CT 101) | `hm1-dmz-guac01` | 14 |
| JMPDMZ-SRV001 (VM 301) | `hm1-dmz-jump01` | 14 |
| k3s control plane / worker | `hm1-int-k3sc01`, `hm1-int-k3sw01` | 14 |
| Keycloak (example app) | `hm1-shr-idp01` | 13 |
| Lab VM for a learning exercise | `hm1-lab-k3sw01` | 14 |
| Future AD domain controller | `hm1-shr-dc01` | 12 |
| UDM Pro Max | `hm1-net-gw01` | 12 |
| USW Pro Max 24 / USW Lite 8 PoE | `hm1-net-csw01` / `hm1-net-asw01` | 13 |
| Access point | `hm1-net-ap01` | 12 |

The network devices' current `lox-*` names (e.g. `lox-gw-01`) move to this pattern when UniFi is renamed (Network Engineer, Class C).

### 2.3 Role codes (seed of `naming/roles.yaml`)

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `pve` | Proxmox VE host | `aiops` | OpenClaw (AIOps team) |
| `cicd` | DevOps plane (Gitea, runner, state DB) | `dns` | DNS resolver/authoritative |
| `dc` | AD domain controller (later) | `idp` | Identity provider (Keycloak etc.) |
| `pki` | Internal CA | `vault` | Secrets store (OpenBao) |
| `jump` | Jump/bastion host | `guac` | Guacamole gateway |
| `rp` | Reverse proxy / ingress | `mon` | Monitoring (Prometheus, Grafana) |
| `log` | Log aggregation | `db` | Shared database server |
| `k3sc` / `k3sw` | k3s control plane / worker | `nas` | Storage/file service |
| `bkp` | Backup server (PBS) | `app` | Single-purpose app with no better code (avoid) |
| `gw` / `csw` / `asw` / `ap` | Gateway / core switch / access switch / access point | `ws` | Windows/Linux workstation |

Role codes are ≤ 5 chars, start with a letter, and describe **function, not product**, unless the product *is* the function (`guac`, `k3sc`). Application Engineer proposes codes for new apps in the app's design note.

---

## 3. Sites, zones, VLANs and IP plan

### 3.1 Zones (current UniFi addressing, kept as is)

Addressing follows the existing UniFi networks exactly. Nothing is renumbered in the rebuild.

| Zone code | UniFi network | VLAN | Subnet | Router (L3) | DHCP | Notes |
|---|---|---|---|---|---|---|
| `net` | Management-Ubiquiti | 1 | 192.168.68.0/24 | `lox-gw-01` | Server | Network devices only |
| `wif` | WiFi | 30 | 192.168.69.0/24 | `lox-gw-01` | Server | Clients, no servers |
| `trn` | Inter-VLAN routing | 4040 | 10.255.253.0/24 | `lox-gw-01` | none | Transit between gateway and core switch. No hosts |
| `tru` | Trusted | 50 | 192.168.73.0/29 | `lox-gw-01` | Server (5 addresses) | Trusted admin endpoints. No servers |
| `shr` | Shared Services | 20 | 192.168.70.0/24 | `lox-coresw-01` | Server | DNS, DevOps plane, IdP, monitoring |
| `int` | Internal | 40 | 192.168.72.0/24 | `lox-coresw-01` | Server | Clusters and internal workloads |
| `dmz` | DMZ | 10 | 192.168.71.0/24 | `lox-coresw-01` | Server | Internet-facing / untrusted |
| `mgt` | Management-InternalServices | 2 | 192.168.67.0/29 | `lox-coresw-01` | Server | PVE host and OpenClaw only (`vmbr0`). **Hard limit: no guest attaches here** |
| `lab` | — | — | — | — | — | No VLAN of its own. Lab guests (VMIDs 8xx) sit in `int` (static IPs `.240–.254`) but keep the `lab` zone code in their names. A dedicated lab network would be a Class C addition by the Network Engineer |

UniFi network names stay as they are. The zone code is the short form used in hostnames, tags, Ansible groups, Terraform stacks, and as Proxmox SDN IDs (≤ 8 chars) if SDN is adopted. Proxmox trunks only `shr`, `int` and `dmz`, plus `mgt` untagged on `vmbr0`. `net`, `wif`, `tru` and `trn` never reach a guest.

### 3.2 Address allocation inside each /24 (`shr`, `int`, `dmz`)

| Range | Use | Assigned by |
|---|---|---|
| `.1` | Gateway (`lox-coresw-01` for `shr`/`int`/`dmz`) | Network Engineer |
| `.2`–`.9` | Network-infra reserved (VIPs for DNS, future anycast, etc.) | Network Engineer |
| `.10`–`.49` | Static infrastructure (DNS, DevOps, DCs, proxies, cluster control planes) | Terraform (IP in code) |
| `.50`–`.99` | Static application and cluster workers | Terraform |
| `.100`–`.199` | DHCP pool | UniFi |
| `.200`–`.239` | Load-balancer / service VIPs (e.g. MetalLB, keepalived) | Terraform/Ansible |
| `.240`–`.254` | Reserved (temporary, migrations). In `int`, this band is where `lab` guests take static IPs | Network Engineer |

The /29 networks don't use these bands:
- `mgt` 192.168.67.0/29: `.1` gateway, `.2` PVE host, `.3` OpenClaw, `.4`–`.6` spare. Nothing else ever.
- `tru` 192.168.73.0/29: `.1` gateway, `.2`–`.6` DHCP for trusted endpoints. No servers.

`net` and `wif` are UniFi-managed (DHCP) and out of scope for guest addressing.

Static addresses are configured in code (Terraform `ip_config`). DHCP reservations are only for appliances that can't take a static IP. Each zone's first service gets `.10`, so `hm1-shr-dns01 = 192.168.70.10`, `dns02 = .11`.

### 3.3 Interface and bridge names
Bridges stay `vmbr<n>` (Proxmox convention). VLAN subinterfaces are `vmbr1.<vlan>`, bonds `bond<n>`. Linux interface names are limited to 15 chars, so don't use descriptive bridge names.

### 3.4 Readdressing: decided, no

Decided 2026-10-03: keep the current UniFi addressing (§3.1). VLAN IDs and third octets don't line up (VLAN 10 → .71, 20 → .70, 40 → .72, 50 → .73). That's fine: names carry the zone, and nothing depends on IPs once DNS is in.

---|---|---|
| **A. Keep subnets (assumed)** | as in §3.1 | None: only Proxmox is being rebuilt, UniFi keeps working |
| B. Align octet to VLAN | VLAN 20 → 192.168.20.0/24 | Re-IP every UniFi network, firewall rule, DHCP and VPN route |
| C. Move to 10/8 per site | `10.<site#>.<vlan>.0/24`, e.g. 10.1.20.0/24 | Same as B, but scales to more sites and avoids clashing with 192.168.x home/VPN networks |

This doc assumes **A**: the zone code in names, not the subnet, carries meaning, and a later move to C stays possible because nothing depends on IPs once DNS is in. If you want B or C, the rebuild is the cheapest moment to do it.

---

## 4. DNS

| Record | Pattern | Example |
|---|---|---|
| Host (A/AAAA + PTR) | `<hostname>.lox-internal.dev` | `hm1-shr-dns01.lox-internal.dev` |
| Service (CNAME → host, or A → VIP) | `<service>.lox-internal.dev` | `git.lox-internal.dev`, `dns.lox-internal.dev` |
| Site-scoped service (only if two sites run it) | `<service>.<site>.lox-internal.dev` | `mon.hm1.lox-internal.dev` |
| Public (published only) | `<service>.loximity.dev` | `guac.loximity.dev` |
| Future AD | `ad.lox-internal.dev`, NetBIOS domain `LOX` | `hm1-shr-dc01.ad.lox-internal.dev` |

Rules:
- The hostname already contains the site, so hosts live directly under `lox-internal.dev`. No site subdomain for hosts.
- Service names are function words, one level, lowercase: `git`, `ci`, `vault`, `idp`, `mon`, `grafana`, `pve`, `aiops`, `proxy`. List in `naming/services.yaml` (stewards: Application Engineer for apps, Network Engineer for infra).
- Internal names are **never** published in `loximity.dev`, and public names never point at private IPs. Two separate domains avoid split-horizon.
- AD later gets its own subdomain (`ad.lox-internal.dev`), so AD never owns the zone the rest of the platform uses. The NetBIOS domain name `LOX` (≤ 15 chars) is reserved now.
- PTR records for every static IP in `192.168.<x>.in-addr.arpa`.
- **Certificates: internal PKI** (decided 2026-10-03). `lox-internal.dev` is not registered publicly and uses no public ACME. All internal TLS certs chain to a self-signed homelab root CA, which is installed on admin endpoints and guests. `.dev` is HSTS-preloaded, so browsers insist on HTTPS: every internal web service needs a cert from that CA before it's used by name. Until the PKI exists, services run on plain HTTP by IP. Note: someone else could register `lox-internal.dev` publicly. Internal DNS answers first, so this only matters for clients that bypass it.

Mapping of current names: `devops.loximity.dev` (mentioned in the network doc) becomes `git.lox-internal.dev`.

---

## 5. VMIDs

**One block of 100 IDs per zone.** The first digit gives the zone, so a guest's ID always matches its hostname's zone code (`hm1-shr-dns01` → 3xx). A guest that moves zone gets a new ID (it's rebuilt or re-imported anyway). IDs are assigned in order and never reused while a backup of the old guest exists.

| Block | Zone | Core `x00–x09` | Workloads `x10–x99` |
|---|---|---|---|
| 100–199 | `mgt` (VLAN 2) | `100` OpenClaw `hm1-mgt-aiops01` | None: the management /29 has room only for the PVE host and OpenClaw. The block exists so the mapping is uniform |
| 200–299 | `dmz` (VLAN 10) | Reverse proxy / jump / gateway services | Internet-facing apps (`hm1-dmz-guac01`, `hm1-dmz-jump01`) |
| 300–399 | `shr` (VLAN 20) | `300` DevOps plane `hm1-shr-cicd01` · `301`/`302` DNS `hm1-shr-dns01/02` · `303` OpenBao `hm1-shr-vault01` (protected, 192.168.70.12) · future DCs, IdP, PBS | Shared services (monitoring, logging, databases) |
| 400–499 | `int` (VLAN 40) | Cluster control planes | Cluster workers, internal apps |
| 500–799 | Reserved | For future zones (e.g. a dedicated lab VLAN or a new site zone), assigned in the next free block | |
| 800–899 | `lab` | `800–849` lab guests, auto-destroyed after 48 h (learning mode) | `850–899` drills and DR restore tests |

Rules inside a block:
- **`x00–x09` core** holds foundational or protected guests of that zone, which other guests depend on. Anything in `protected.yaml` sits here.
- **`x10–x99`** holds everything else, assigned in order.
- `net`, `wif`, `tru` and `trn` never host guests, so they get no block.

Not zones, so outside the scheme:

| Range | Use |
|---|---|
| 9000–9099 | Linux templates |
| 9100–9199 | Windows templates |
| 9900–9999 | Temporary (imports, conversions): never long-lived |

**Knock-on change:** the hard limits (Proxmox ACL `NoAccess` on `/vms/106` and `/vms/107`, the Terraform guard, the classifier and the MCP tools) must move to the new platform VMIDs **in the same change** that creates them. Keep the protected list in one file, `protected.yaml` in `homelab-standards` (§1.1), read by all four, instead of hard-coding the numbers. Only Faris can change it.

---

## 6. Proxmox objects

### 6.1 Node and cluster
Node = hostname (`hm1-mgt-pve01`). Future cluster name: `hm1-pvc01` (cluster names ≤ 15 chars).

### 6.2 Storage IDs
`<type>-<media><nn>`: `lvmt-nvme01`, `lvmt-sata01` (live since 2026-10-03), future `zfs-ssd01`, `dir-backup01`, `nfs-nas01`, `pbs-bkp01`. Type ∈ `lvm|lvmt|zfs|dir|nfs|cifs|pbs|ceph`. `local` and `local-lvm` stay as Proxmox ships them unless the disk layout changes.

### 6.3 Pools
One pool per zone: `pool-mgt`, `pool-dmz`, `pool-shr`, `pool-int`, `pool-lab` (created 2026-10-03). Pools drive permissions, so keep them few and stable.

### 6.4 Templates
`tpl-<os><version>-<variant>`, no site or zone. Examples: `tpl-ubuntu2604-base` (9000), `tpl-debian13-base`, `tpl-win2025-core` (9100), `tpl-win2025-gui` (9101). LXC templates keep upstream file names in `local:vztmpl`.

### 6.5 Tags (controlled, `key-value`, lowercase)
Proxmox tags allow `a-z 0-9 - _ +`, so tags are `key-value`:

| Key | Values | Required |
|---|---|---|
| `zone-` | zone codes | yes |
| `role-` | role codes | yes |
| `mgd-` | `tf` (Terraform), `manual`, `lab` | yes |
| `owner-` | `infra`, `sys`, `app`, `net`, `sre`, `faris` | yes |
| `os-` | `ubuntu2604`, `debian13`, `win2025`, … | yes |
| `patch-` | `ring0` (manual, e.g. CT 100 and 300), `ring1` (auto Sev1/2), `ring2` | yes |
| `env-` | `prod`, `lab` | optional |
| `protected` | (no value) | on hard-limited guests only |

`mgd-manual` must be the exception: the rebuild aims for every non-lab guest to be `mgd-tf`, including those built "outside DevOps" today.

### 6.6 HA groups, firewall aliases, IP sets, security groups
Proxmox firewall objects: alias `<zone>-<hostname-role>` (e.g. `shr-dns`), IP set `ipset-<zone>-<purpose>`, security group `sg-<role>` (e.g. `sg-dns`). HA groups: `ha-<purpose>`.

---

## 7. Identities

| Kind | Pattern | Examples | Notes |
|---|---|---|---|
| Human | first name / initials, lowercase | `faris` | Same across Gitea, Proxmox (`faris@pve`), Linux, later AD (`sAMAccountName` ≤ 20 chars) |
| Human admin (separate privileged account) | `adm-<user>` | `adm-faris` | Day-to-day `faris` has no admin rights once AD arrives |
| Service account | `svc-<system>-<purpose>` | `svc-tf-plan@pve`, `svc-tf-apply@pve`, `svc-metrics@pve`, `svc-patcher` (Linux) | ≤ 20 chars so it fits AD later |
| Proxmox API token | `<user>!<purpose>` | `svc-tf-apply@pve!pipeline` | One token per consumer |
| AI agent identity | `oc-<agent>` | `oc-pm`, `oc-infra`, `oc-sys`, `oc-app`, `oc-net`, `oc-rev`, `oc-sre`, `oc-tutor` | Matches the 8-agent team. Used in Gitea, audit log and SSH keys |
| CI bot | `ci-<purpose>` | `ci-merger`, `ci-runner` | |
| Group / role | `grp-<scope>-<right>` (groups), PascalCase (Proxmox roles) | `grp-pve-operators`; roles `DevOpsEngineer`, `DevOpsPlan`, `OpenClawOperator` | |
| SSH key comment / file | `<identity>@<origin>`, `id_ed25519_<identity>` | `oc-sys@hm1-mgt-aiops01` | Key file names, not reused across identities |

Shared admin accounts (`root` login, `devops-admin`) are break-glass only and listed as such in `docs/identities.md`.

---

## 8. Code and repo

### 8.1 Terraform (Infrastructure Engineer)
- Stacks: `terraform/stacks/<site>/<zone>/` (e.g. `stacks/hm1/shr/`); provider-specific stacks `terraform/stacks/<site>/unifi/`.
- Modules: `terraform/modules/<kind>` — `lxc`, `vm`, `vm-windows`, `pool`, `dns-record`.
- Resource keys = hostname with `-` → `_`: `module "hm1_shr_dns01"`, or one `for_each` map keyed by hostname (preferred).
- Variables, locals, outputs: `snake_case`, units in the name (`disk_gb`, `memory_mb`).
- State keys / workspaces: `<site>-<zone>` (`hm1-shr`).

### 8.2 Ansible OS layer (Systems Engineer)
- Inventory hosts = hostnames. Groups: `site_hm1`, `zone_shr`, `role_dns`, `os_ubuntu`, `patch_ring1`, generated from Proxmox tags, so tags and groups never disagree.
- Roles: `base_*` (every host: `base_users`, `base_ssh`, `base_hardening`), `os_*` (`os_ubuntu`, `os_windows`), `bb_*` building blocks shared with apps (`bb_postgres`, `bb_nginx`, `bb_docker`, `bb_certs`).
- Playbooks: `site.yml`, then `<layer>-<purpose>.yml` (`patch-apply.yml`, `base-harden.yml`).
- Variables: role-prefixed `snake_case` (`base_ssh_port`, `bb_postgres_version`).

### 8.3 Applications (Application Engineer)
- App roles: `app_<name>` (`app_keycloak`, `app_gitea`). Design note `docs/apps/<name>.md`, runbook `docs/runbooks/app-<name>.md`.
- App config in `apps/<name>/` (rendered config, compose files, Helm values).
- Containers / compose projects / k8s namespaces: `<name>` (lowercase, no env suffix: the zone gives the environment). k8s labels follow `app.kubernetes.io/name`.
- Service DNS names per §4, registered in `naming/services.yaml`.

### 8.4 Git (Infrastructure Engineer)
- Repos: `<org>/<scope>-<purpose>` (`homelab/homelab-infra`; new repos only per the repo strategy in `architecture-devops.md` §12).
- Branches: `<type>/<issue#>-<slug>`. Types: `feat`, `fix`, `chore`, `patch`, `app`, `net`, `learn`, `docs`. Example `feat/42-shr-dns-pair`.
- Commits: Conventional Commits with zone scope: `feat(shr): add dns01/dns02`.
- Labels: `class/a`, `class/b`, `class/c` (classifier), `wip`, `agent/<agent>`, `sev/1`–`sev/4`, `learn`.
- Release tags: `vYYYY.MM.DD[.n]`.

### 8.5 Secrets (Infrastructure Engineer)
- Files: `secrets/<site>/<zone|platform>/<system>.sops.yaml` (e.g. `secrets/hm1/platform/gitea.sops.yaml`).
- Keys: `UPPER_SNAKE`, `<SYSTEM>_<PURPOSE>_<KIND>` (`GITEA_CIMERGER_TOKEN`, `PVE_TFAPPLY_TOKEN_SECRET`, `PG_TERRAFORM_PASSWORD`). `KIND` ∈ `TOKEN`, `PASSWORD`, `KEY`, `CERT`, `URL`.
- age recipients: `age-<holder>` (`age-faris`, `age-ci`, `age-aiops`).

---

## 9. Ops artefacts

### 9.1 Alerts, runbooks, dashboards (SRE)
- Alert names: PascalCase `<Component><Condition>` (Prometheus convention): `HostDiskHigh`, `GuestDown`, `DnsResolverDown`, `BackupMissed`.
- Labels on every alert: `severity` (`critical|warning|info`), `zone`, `role`, `host`, `owner`.
- Runbook = `docs/runbooks/<AlertName>.md`, linked from the alert's `runbook_url`.
- Dashboards: `<Scope> / <Subject>` (`Platform / Proxmox host`, `Zone / SHR`).

### 9.2 Snapshots and backups (SRE)
- Snapshot names (Proxmox: start with a letter, `A-Za-z0-9_-`, ≤ 40 chars): `<reason>_<yyyymmdd>_<hhmm>`. Reasons: `pre-patch`, `pre-change`, `pre-upgrade`, `manual`, `drill`. Example `pre-patch_20261025_0200`. Snapshots older than 7 days without `manual` are flagged.
- Backup notes template: `{{guestname}} {{vmid}} zone={{zone}}`. Backup jobs: `bkp-<zone>-<schedule>` (`bkp-shr-daily`).

### 9.3 Patch artefacts (Systems Engineer)
PR titles `patch(<ring>): Sev<n> <yyyy-mm-dd>`; monthly bundle branch `patch/<yyyy-mm>-bundle`; approval issues `reboot: <hostname> <yyyy-mm-dd>`.

### 9.4 Learning artefacts (Tutor)
`docs/learn/<yyyy-mm-dd>-<slug>.md`, issues labelled `learn`, drills `drill-<topic>` with VMIDs 850–899.

---

## 10. Changing a convention

1. **Need spotted** (an agent needs a new role code, service name or tag value, or a rule doesn't fit): the steward opens an issue in `homelab-standards` with the proposed value and why, and links the blocked PR. The blocked PR stays red until the value exists. No workaround names.
2. **Faris decides** and edits `homelab-standards` himself: web edit or push to `main`.
3. **Pick-up:** the next pipeline run uses it, the agents' clone refreshes within 15 min, and the steward re-runs the blocked PR.
4. **Renames of existing things** are normal `homelab-infra` changes with their own class (rename of a host = rebuild or DNS cutover, planned by the steward).

Learning tip: editing the YAML yourself is a quick way to see the gate react. Add a role code, then watch a previously failing PR go green.

---

## 11. Enforcement (`lint/naming.py` from `homelab-standards`, run in the `homelab-infra` PR gate)

| Check | Rule |
|---|---|
| Hostname | `^hm1-(mgt\|net\|dmz\|shr\|int\|lab)-[a-z][a-z0-9]{1,4}[0-9]{2}$`, length ≤ 15, role ∈ `roles.yaml`, zone matches the VLAN of the primary NIC; `net`/`wif`/`tru`/`trn` are rejected for guests |
| VMID | within the zone's range (§5); not in `protected.yaml` unless the PR is Class C |
| IP | inside the zone subnet and the right allocation band (§3.2); no `.100–.199` statics |
| Tags | all required keys present, values from vocab (§6.5); `zone-` tag = hostname zone |
| DNS | service names ∈ `services.yaml`; no `lox-internal.dev` names in `loximity.dev` zone |
| Identities | match §7 patterns, ≤ 20 chars |
| Secrets | file path and key regex (§8.5) |
| Snapshots | name regex (§9.2) for snapshots created by tools |
| Git | branch regex and Conventional Commit title |

Agents get the same rules as a short skill (`naming`) so they produce valid names first time instead of discovering them in CI. That keeps token use down too.

---

## 12. Rebuild checklist (naming-related)

1. Confirm site code (`hm1`).
2. Stand up the internal PKI (self-signed root, issuing CA) and distribute the root to admin endpoints.
3. Create `homelab-standards` (Faris-only write, agents read) with `naming/*.yaml`, `protected.yaml` and `lint/naming.py`, and wire it into `pr.yml` and the CT 106 clone **before** the first guest PR.
4. Build DNS first (`hm1-shr-dns01/02`, VMIDs 301/302, `.10/.11`) so every later guest registers by name.
5. Rebuild the platform at VMIDs 100 (OpenClaw, `mgt`) and 300 (DevOps plane, `shr`), with `protected.yaml` pointed at the new IDs in the same change.
6. Import or rebuild every other guest under the new names. Nothing stays `mgd-manual` without a recorded reason.
7. Update agent prompts and skills (CT 100) to the new names and docs.
