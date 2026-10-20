# Connected local workflow · v0.11

Use this for compound questions, recommendations and map delivery. No MCP, LLM API, account, save parser or live server connection is installed. Python uses only the standard library.

## 1. Make the interpretation reviewable

From the skill directory:

```sh
python3 scripts/workflow.py draft --question 'Find 3 coal clusters near unlocked fast travel' --profile /absolute/path/player.json --output /absolute/path/task.json
```

The optional local profile accepts only `version`, `platform`, `mode`, `level`, `owned_pals`, `inventory`, `unlocked_fast_travel`, and `position`. Species/travel fields are lists of exact names, inventory maps item names/IDs to nonnegative integers, and position is `[X,Y]`. Supply current facts; do not carry old chat state forward without confirmation. The latest explicitly spoken level overrides the supplied profile. Profile persistence is explicit file reuse, not an automatic cross-chat memory.

The task contains `schema: 1`, `question`, `language` (`zh` or `en`), `context`, `assumptions`, `missing_information`, and `steps`. Assumptions describe a `field`, `value`, and `reason`; missing-information entries identify `field`, `reason`, and the step IDs they `blocks`.

`draft` handles common resource locations, explicit species routes, parent pairs, named crafting targets, mount/work comparisons, server symptoms and one supplied fixed drop rate. It supports selected Chinese/English expressions. It cannot understand arbitrary natural language, extract every observation or create a complete acquisition plan automatically. The host reads the original question, checks all goals and values, then edits/adds explicit steps. Unknown/multiple targets, unresolved resources, missing position/unlocked travel, individual breeding optimization and unsupported ranking remain gaps; public requests outside the parser route to recorded research. Preserve those gaps rather than deleting them to obtain a green report.

## 2. Connect existing tools

Each ordered step has:

```json
{"id":"details","tool":"pal","arguments":{},"depends_on":["breed"],
 "bindings":{"name":{"step":"breed","path":["target","name"]}}}
```

Bindings read the **data** of an earlier dependency, with an explicit list of dictionary keys/list indexes. No expressions, shell interpolation or arbitrary commands execute. Dependencies must be earlier steps; cycles and duplicate IDs are rejected. Dependencies mean data flow, not proof that an action occurred in game. `already-owned`, `species-route-found` and `no-route-within-limit` must still be interpreted separately.

| Step tool | Arguments and actual underlying operation |
|---|---|
| `breed` | `target`, `owned`, optional `max_generations`; PalCalc species planner |
| `pair` | `parents` list of two names, optional `verify_online`; optional independent API check |
| `pal` | `name`; exact public API record |
| `craft` | `item`, optional `quantity`, `inventory`; source-checked direct deficits |
| `compare` | Existing `pal_compare.compare` fields, e.g. `kind`, `level`, `names`, `limit` |
| `entry` | Verified article `slug`, section `contains`, optional `max_chars` |
| `locations` | `category`, `purpose`, `count`, `sort`, optional `near`, `radius`, `unlocked_fast_travel` |
| `map` | Bind `points` to the complete `locations` data; optional `title` |
| `odds` | `percent`, `runs`, optional `target`; supplied independent fixed rate |
| `chain` | `stages`, optional `runs`, `target`, `retry_wait_minutes`; explicit conditional sources |
| `revisit` | `last_cleared`, `minimum_minutes`, `maximum_minutes`; timezone required |
| `server` | Existing `inspect_server` inputs or `files` mapping `world_text`, `mod_text`, `log_text`, `manifest` to supplied local paths |
| `sources` | Optional `topic`, `question`; directory, not retrieved evidence |
| `research` | Focused public `question`, optional `topic`; host search/read receipts and resume |
| `fetch` | `source_id`, optional `contains`, `max_chars`; registered public page excerpt |

For `locations`, `sort` is `source`, `fast-travel`, or `near`. Nodes preserve that ordering. Clusters and base candidates prioritize record count, then the selected ordering as tie-break. The radius is in game coordinate units, not metres or mining reach. Duplicate coordinates count once. Candidate centres are actual sourced nodes; each neighbourhood contains records within radius. Greedy disjoint neighbourhood selection does not claim a globally optimal clustering. `base-candidates` always retains terrain, build permission, radius fit, risk and access checks as unresolved. The main map is the only calibrated map.

## 3. Execute once, preserve evidence

```sh
python3 scripts/workflow.py run --task /absolute/path/task.json --output-dir /absolute/path/new-run --offline
```

Omit `--offline` for public reads; `--refresh` and `--cache-dir` retain existing adapter policies. Offline breeding works on a fresh installation. This public candidate omits saved community recipe examples; offline API records, recipe checks and map tiles require a populated cache. Offline is never a live verification claim. The runner does not retry failed network operations automatically. Inspect HTTP status, source structure and existing dated cache before a host/browser fallback.

Outputs are `task.md`, `run.json`, `review.json`, and per-map SVG/evidence files. Existing run directories are refused. Each step envelope contains `schema`, `tool`, `status`, `data`, `evidence`, `retrieved_at`, `version_scope`, `conflicts`, `gaps`, `next_steps`, and `artifacts`. Status is `completed`, `partial`, `blocked`, `failed`, or `awaiting-research`. Incomplete built-ins and uncovered public requests use the [research handoff](research.md); the host searches/reads, records evidence and resumes without asking the player to move files. A tool completing does not mean the final answer is ready. Missing fields block the affected steps and their dependencies; independent steps continue. A partial result may still contain useful data, e.g. mapped scouting candidates with unverified terrain.

Raw server inputs are omitted from generated task/run reports; the original task and supplied files remain local. A player's question/context can still be private. Never bundle profile, task or run records in the distributed skill. Source URLs/time/hash/cache metadata are evidence provenance, not proof of source truth. Provider build metadata is not automatically matched to the player's version, and some sources lack machine-readable versions.

## 4. Deliver and inspect the actual answer

Use the run to write the answer in the player's language. Include useful next steps, explicit assumptions, limits and supporting source links. Location answers need numbered coordinates to **two decimal places**, the real map link, and source URLs; source precision is not an in-game accuracy claim. Include cluster counts/radius when density drove selection. Label base candidates as unverified scouting candidates.

```sh
python3 scripts/workflow.py review --run /absolute/path/new-run/run.json --answer /absolute/path/answer.md --output /absolute/path/new-run/final-review.json
```

The structural checker detects missing or altered map artifacts, mismatched point records, missing coordinate pairs/map references, absent per-step source links, undisclosed assumptions, unresolved tool gaps, and absent candidate-specific acquisition sections. For comparisons, restrict candidates to those actually being presented; add dependent `entry` steps for each candidate's actual acquisition evidence. `requires: ["acquisition"]` also enables this check on a species plan. Section matching and identity links are only evidence to inspect: the host must determine whether they support capture, breeding, saddle availability, level and current version.

An initial run always has `answer-not-reviewed`. `ready-for-human-review` means only that structural checks passed. It does not certify source semantics, feasible ownership/genders, actual render readability, language purity, terrain suitability, safety, yields, or final-answer truth. If real gaps remain, return a useful partial answer and say what is missing; do not call a partial result fully verified.

## 5. Evaluate the full path honestly

Test at three levels: bilingual question-to-task routing; real adapter/dependency/artifact execution; and the host's final answer with map/source inspection. Include missing-context, conflicting-source, unavailable-source, altered-artifact and unsupported-request cases. Fixture-based routing and same-host answer replay are not independent model evaluations. Preserve an earlier baseline and report remaining limits.
