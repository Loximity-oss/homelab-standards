# README standard

| | |
|---|---|
| **Applies to** | The root `README.md` of every repo in the Gitea organization `homelab`: `homelab-infra`, `homelab-apps`, `homelab-standards`, `openclaw` |
| **Language** | ASD-STE100 (Simplified Technical English) |
| **Revision history** | The Git history of the repo |
| **Owner** | Faris. Class C |

## 1. Scope

- Every repo has one root `README.md`. It has the 12 headers in section 3, in the same order.
- A folder can have a short README. Section 5 gives the form.
- A design document is not a README. Do not apply this standard to it.

## 2. Language: ASD-STE100

Write every README in ASD-STE100. Use the current issue of the specification from `asd-ste100.org`.

| Rule | How to apply it |
|---|---|
| Sentence length | Use at most 20 words in an instruction. Use at most 25 words in a description. |
| Paragraph | Write one topic in each paragraph. Use at most 6 sentences. |
| Instruction | Use the imperative. Write one action in each sentence. Example: "Run `plan`." |
| Voice and tense | Use the active voice. Use the simple present tense where possible. |
| Words | Use one word for one meaning. Use words from the STE dictionary and the term list in section 7. |
| Articles | Keep "the" and "a". Do not remove them. |
| Noun string | Use at most three nouns in a row. |
| Style | Do not use contractions, idioms, or slang. |
| List | Use a vertical list for steps and for items in a series. |
| Safety text | `Caution:` means risk of damage to a system or to data. `Warning:` means risk of injury. `Note:` means other information. |
| Technical names | Write host names, file names, tool names, and zone names in code format, exactly as the system shows them. |

## 3. The 12 headers

Use the heading text in the table. Use `##` for headers 2 to 12.

If a header does not apply, keep it. Write `Not applicable: <reason>.` under it.

| # | Heading | Content |
|---|---|---|
| 1 | `# <repo name>` | The title. Below it, one paragraph: what the repo owns, and what it does not own. |
| 2 | `## Status` | State (live or planned). The date of the last check. The pipeline or host that uses the repo. |
| 3 | `## Place in the system` | A table of the four repos and how they relate. Mark this repo. |
| 4 | `## Layout` | The folders and key files. One short line for each. |
| 5 | `## Change process` | Branch and title format. The change class (A, B, C) for this repo. Who approves and who merges. The checks that run. |
| 6 | `## Write access` | Who can write: people, agents, pipeline. The source of the rule (for example `owners.yaml`). |
| 7 | `## Key concepts` | The model of this repo. Example: the guest spec, the catalogue entry, the agent roles. |
| 8 | `## Local checks` | The commands to test a change before the PR. How to read the result. |
| 9 | `## Operations` | Schedules, runners, locks, and where the logs are. |
| 10 | `## Secrets and safety` | Where the secrets are. The hard limits. Use `Caution:` for each limit. Never write a secret value. |
| 11 | `## Documents` | Links to the folder `docs/` and to the other documents about this repo. |
| 12 | `## Known gaps` | Gaps that are true now. Describe each gap. Do not add an issue number. |

## 4. What a README does not contain

| Do not write | Reason |
|---|---|
| Issue, PR, or project numbers and links | Git history is the record. |
| The name or date of a past event: a move, an outage, a decision | Git history holds these. |
| A secret value, token, or key | A README is public to every reader of the repo. |
| A value that changes every day: counts, commit hashes, open items | The value is wrong after one day. |
| A reference table of more than 10 rows | Put the table in `docs/` and link to it. |

You can write a date in header 2 (`Status`) for the last check. Do not write a date anywhere else.

## 5. README in a folder

Use this form for a README below the root.

1. Title: `# <path>`. Below it, one sentence for the purpose.
2. `## Contents`: the files and what each one does.
3. `## Use`: the steps or commands.
4. `Caution:` line if the folder is Class C or runs as root.
5. Last line: `Back to the root README: <relative path>`.

Use at most 60 lines.

## 6. Record of changes

The revision history of a README is the Git history of the repo. Do not add a `CHANGELOG.md` or a revision table.

A change is material when it changes one of these:
- the live behavior of a system
- a change class or a write scope
- a schedule
- a guest
- a secret path

Each commit for a material change follows these rules:
- The subject follows the Conventional Commit format in `naming-conventions.md` section 8.4.
- The body says what changed and why.
- If the change makes a README fact false, the same commit corrects the README.

The Reviewer (`oc-rev`) checks these rules. No tool enforces them yet.

## 7. Term list

Use each term for one meaning only. Do not use the words in the last column.

| Term | Meaning | Do not use |
|---|---|---|
| guest | An LXC container or a VM on Proxmox | host, CT, container, machine |
| host | The physical Proxmox node `hm1-mgt-pve01` | server, box |
| site | One installation, for example `hm1` | location |
| zone | A network segment with one VLAN, one subnet, and one code | network, VLAN (alone) |
| protected | Listed in `protected.yaml`. Agents and the pipeline never change it | locked, reserved |
| class | The gate level of a PR: A, B, or C | tier, level |
| plan | The Terraform preview of a change | dry run |
| apply | The step that makes the change live | roll out, push |
| deploy | The step that puts an application on a guest | install, release |
| verify | The read-only check of the state after a change | test (for live checks) |
| drift | A difference between Git and the live system | skew |
| wave | A group of guests that a deploy updates together | batch, phase |
| ring | The patch group of a guest: `ring0`, `ring1`, `ring2` | group, stage |
| runner | A Gitea Actions worker on `hm1-shr-cicd01` | agent (for a CI worker) |
| agent | An OpenClaw AI role, for example `oc-infra` | bot |
| merge broker | The timer job that merges a PR after the gate passes | auto-merger |

## 8. Check

The Reviewer checks a README change against this standard. A tool check is not built yet.
