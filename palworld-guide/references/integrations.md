# Integrated shortcuts · v0.4

Use these fixed adapters before rediscovering the same sites by search. They read public data and run locally through the assistant's terminal. All Python dependencies are standard-library modules.

## What is reused

| Provider | Integration | Provenance and boundaries |
|---|---|---|
| [PalCalc, Tyler Camp](https://github.com/tylercamp/palcalc) | Normalized English species and explicit parent/child/gender records | Fixed revision `66f18a000e2107640b219562437357ced5aff7eb`, dataset `v28`, 299 species and 44,851 records. MIT notice in `assets/LICENSE-PalCalc.txt`. This is data reuse, not execution of the full PalCalc solver. |
| [PalDB.gg public API](https://paldb.gg/developers/) | Exact Pal/item lookup, recipe records and optional parent-pair cross-check | Independent of PalDB.cc. API envelope carries `gameVersion`, provider verification time and attribution. The build identifier is not silently translated to a player game version. |
| [PalDB.cc](https://paldb.cc/en/) | Independent production-row check, existing comparison tables and map adapter | Preserve source role and retrieval metadata. Recipe disagreement is explicit; map calibration remains main-map only. |

Our adapter code resolves identities, caches responses, checks schema/build consistency, assembles species-level steps, subtracts inventory, and exposes short commands. Upstream data, the upstream full solver and game assets are credited to their respective authors. The live API is not claimed to be Pocketpair's official API.

## Owned Pals to a target

```sh
python3 scripts/companion.py breed --target Pyrin --owned Bushi Penking Vanwyrm
python3 scripts/companion.py breed --target Anubis --owned Dualith Blazamut --max-generations 6
python3 scripts/companion.py pair --parents Bushi Penking
python3 scripts/companion.py pair --parents Bushi Penking --verify-online
```

These are queries against the pinned current dataset, not permanent remembered recipes. Exact English species names, internal IDs and the bundled provenance-backed Chinese aliases are accepted; ambiguous or unknown names stop with suggestions. The alias map reuses the same pinned PalCalc locale and saved public item labels as the webpage (`name-aliases.json`); it does not translate arbitrary names or fuzzy-match variants. Species-level planning uses only listed owned species and produced children. It minimizes dependency generations in the snapshot, with a stable tie-break; the displayed operation count is for the returned plan, not a global minimum. Shared produced species are reused in its dependency graph.

The roster is a list of species, not proof of compatible individual genders. Read each step's upstream gender requirements. Confirm compatible sexes, cake supply, facilities and game version before acting. Passives, IVs, mutation odds, hatch times, duplicate individual availability and expected eggs are not solved here. Use the full MIT PalCalc application when that deeper optimization is needed.

`already-owned`, `species-route-found` and `no-route-within-limit` are different outcomes. No route within a bound is not proof that the species is impossible to obtain.

## Exact API records

```sh
python3 scripts/companion.py pal --name Anubis
python3 scripts/companion.py recipe --item 'Legendary Sphere'
```

The adapter resolves exact names against the documented search endpoint, then requests the returned internal ID. It does not accept an arbitrary URL. Fields retain provider semantics: a spawn summary is not every spawn point, and work suitability is not measured throughput. Pair verification sends the two public species IDs, not a raw roster file.

## Direct missing-material totals

```sh
python3 scripts/companion.py craft --item 'Legendary Sphere' --quantity 100 --inventory inventory.json
```

Example local `inventory.json`:

```json
{"Stone":500,"Paldium Fragment":100}
```

The target's ordinary recipe is retrieved from PalDB.gg and compared with the linked ingredient counts and batch yield in PalDB.cc's Production table. Only agreement yields one material-deficit total. Each response retains raw build identifiers, retrieval dates, hashes and attribution. `recipe-evidence-incomplete` returns the provider evidence when they disagree or the cross-check cannot be completed. It does not manufacture a total or silently choose a source.

Counts are direct ingredients, not recursive raw-material expansion. Batch output is rounded up and inventory is subtracted once per distinct material. English/Chinese names and IDs are accepted; providing multiple aliases for the same ingredient is rejected before arithmetic. Known translated item names also work for the two bundled offline recipe targets. Unknown inventory entries are returned visibly. Inventory and quantities are not sent to the provider: public requests contain only the target/material names or IDs required to retrieve game data.

This iteration reproduced a source disagreement for Pyrin Saddle (a Paldium Fragment ingredient appears in one provider's ordinary row but not the other's). It is retained as a conflict example, not used as a single settled material list. The Legendary Sphere example agreed across providers at retrieval time. Agreement is not independent in-game verification.

## Network behavior

API operations support `--offline`, `--refresh` and `--cache-dir PATH`. API responses use a one-hour cache; the provider documents anonymous limits of 300 requests/hour. Each command allows at most twelve API calls, makes no automatic retries, and stops on HTTP or schema errors. A version change inside one operation stops it from mixing builds. Public browsing and map caches keep their existing policy. No API key or account is required for these public reads.

The included breeding snapshot works without network access. This public candidate omits saved recipe cross-check examples; `craft`/`recipe --offline` needs a previously populated public cache. The local development edition may carry additional saved examples, but they are not distributed here. `--refresh` and `--offline` cannot be combined. Public sample recipes support the offline webpage. Refresh maintained data explicitly with the project `scripts/refresh_integrations.py`; ordinary builds do not call providers. No downloaded code is evaluated or installed.
