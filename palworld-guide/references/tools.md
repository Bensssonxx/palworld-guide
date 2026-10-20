# Executable tools · v0.10

For connected task execution, reusable local player context, purpose-specific location selection, uniform result envelopes and final-answer checks, use [the workflow entry point](workflow.md). Its `workflow.py` wrapper keeps the existing direct commands below compatible.

Run from the skill directory, or use an absolute script path. All scripts use Python's standard library. The assistant supplies interpretation; these scripts are not a separate language model or registered MCP server. Network tools read public sources only. No private configuration is uploaded.

## Sources

```sh
python3 scripts/public_sources.py sources --topic mods --question 'Workshop mod missing on a dedicated server'
python3 scripts/public_sources.py fetch --source official-mods --contains IsServer
python3 scripts/public_sources.py fetch --source official-config --contains PalStomachDecreaceRate
```

The registry distinguishes official specifications, author compatibility, provider instructions, community-maintained troubleshooting, and community data. Run returned site queries through the host's search tool when the registry page is only an entry point. Fetch output includes retrieval time, content hash, observed version labels, a bounded excerpt and match status. It never executes downloaded JavaScript.

Public pages and map tiles are cached for 24 hours in the system temporary directory. Use `--refresh`, `--offline`, or `--cache-dir PATH` as needed. Offline results retain their retrieval time and stale flag. Missing or changed source structure is a reason to inspect the page, not invent a result.

## Pal comparison and article lookup

```sh
python3 scripts/pal_compare.py compare --kind ground --level 52 --baseline Fenglope --sort sprint --limit 8
python3 scripts/pal_compare.py compare --kind ground --names Fenglope Pyrin Rayhound --sort stamina
python3 scripts/pal_compare.py compare --kind mining --names Digtoise Dumud Astegon
python3 scripts/pal_compare.py compare --kind handiwork --limit 8
python3 scripts/pal_compare.py entry --slug Fenglope --contains 'Partner Skill'
```

The parser reads current English source tables, including optional HTML closing tags. It rejects changed headings or incomplete rows. Ground-mount output keeps Run Speed, Ride Sprint Speed, Tech Level and Stamina separate. The level filter applies only to the listed technology requirement: ownership, wild encounter level, breeding and saddle crafting materials still need checking. A Pareto marker means no other eligible row has both at least as much sprint speed and stamina with one strict improvement; it does not imply universal superiority. It is computed before limiting the output.

Work comparisons preserve the source's `Level` and `4 Level` columns as `listed_work_level` and `four_star_work_level`. They do not estimate capture difficulty or measured productivity. No player-level filter is accepted for those tables. Partner skills, upgrades and global research must be checked separately.

`entry` returns matching text plus up to twenty relevant same-site `article_links` with labels and section names; site navigation is excluded. Follow the actual link before treating it as acquisition evidence. An absent `MagazineSize` or shot-count field does not establish how many projectiles fire per trigger pull.

`entry` accepts an English article slug from a verified PalDB link, such as a Pal, weapon or ammunition article. It returns matching surrounding text, not a generated explanation. An unmatched section remains unknown. Use acquisition sections to distinguish wild spawns, Alpha encounters, breeding and eggs; use exact ammo fields for compatibility rather than assuming a higher-tier cartridge works.

## Real map lookup and marking

```sh
python3 scripts/map_tools.py locate --query coal --category Coal --sort fast-travel --min-separation 80 --limit 5 --output coal-points.json
python3 scripts/map_tools.py mark --points coal-points.json --title 'Coal near fast travel' --embed-tiles --show-fast-travel --output coal-map.svg
python3 scripts/map_tools.py locate --category Dungeon --near 0 0 --limit 5
```

The final command demonstrates argument syntax, not a recommended starting location. Use an actual source category; inspect the dataset if a translated category yields no match. `--near X Y` and nearest-fast-travel results use straight-line coordinate distance, not a traversable route or an altitude-aware path. Never equate a dungeon entrance with its interior rewards.

The main-map adapter reads the current English PalDB dataset and checks the provider's coordinate transform and bounds. Changed calibration stops plotting. `mark` creates numbered markers, real terrain tiles, coordinates, source links and an adjacent `.evidence.json` containing unrounded coordinates and projected pixels. Use `--language zh` for Chinese map captions, sourced location labels and provenance text (keep source URLs and identifiers exact). `--show-fast-travel` adds distinct T badges, source coordinates and matching nearest-travel names without changing resource coordinates.

`--embed-tiles` makes the SVG independent of later tile requests; modern browsers render its embedded WebP images. Some SVG rasterizers do not support embedded WebP. Existing outputs are preserved.

Optional PNG shortcut: `python3 scripts/map_preview.py --svg /absolute/path/map.svg --output /absolute/path/map.png`. Use an existing Python with Pillow and an existing `rsvg-convert`; no dependency is installed by this command. It converts embedded tiles before rendering to prevent blank terrain, rejects external/active SVG content, preserves the original SVG/evidence and refuses overwrites. Missing optional tools return an explicit browser-SVG fallback. Open the actual result before claiming a visual inspection.

Manual points need a source and an honest status:

```json
{"map_id":"palpagos-main","points":[{"label":"User supplied point","x":0,"y":0,"source_url":"https://paldb.cc/en/Palpagos_Islands","status":"user-provided"}]}
```

This `(0,0)` is schema syntax, not a gameplay claim. World Tree interiors are not calibrated in this version and other map IDs are rejected. A map record can be a camp anchor, not the exact final chest. Terrain belongs to Pocketpair; map tiles and data are provided by PalDB. Generated images retain attribution.

## Conditional reward chains and revisit windows

```sh
python3 scripts/farm_plan.py chain --input route.json --runs 20 --target 0.95 --retry-wait 0
python3 scripts/farm_plan.py revisit --last-cleared 2026-10-19T14:00:00-04:00 --minimum-minutes 30 --maximum-minutes 40
```

`route.json` contains conditional stages. The numbers below are **synthetic arithmetic examples**, not game drop rates:

```json
{"stages":[
  {"label":"Obtain the intermediate reward","conditional_percent":50,"minutes":8,"source_url":"https://example.com/example-stage-a"},
  {"label":"Open it for the target","conditional_percent":10,"minutes":2,"source_url":"https://example.com/example-stage-b"}
]}
```

The route succeeds with probability `0.5 × 0.1 = 0.05`. Stage two is entered only after stage one succeeds, so expected active minutes per attempt are `8 + 0.5 × 2 = 9`. If a failed attempt is followed by wait `w`, expected minutes until first success are `(expected_active_cost + (1-p) × w) / p`. The first attempt starts immediately. All complete attempts must have independent fixed outcomes; stage probabilities are conditional on reaching the stage. Missing rates, table weights, batch reward draws or correlated retries require a different model.

A real route must cite the specific reward/container table at each stage. The tool validates numeric inputs and source URL shape, not source truth. Compare routes under the same cost and timing assumptions. Expected time is not a guarantee. `revisit` only calculates a timezone-aware check window from a supplied interval; the example 30–40 minutes is not a verified Palworld timer. It creates no reminder or background automation.

## Read-only server inspection

```sh
python3 scripts/server_check.py --world-config PalWorldSettings.ini --mod-config PalModSettings.ini --info Info.json --log recent-UE4SS.log --os windows --food available --output server-report.json
```

Supply only files you have. Optional arguments include `--revision INTEGER`, `--stuck yes`, and `--manual-loader --workshop-loader` when both methods really are present. Version strings and game revisions are different.

Checks cover the default template versus active configuration; hunger and drop-quantity parameters; global mod activation (including invalid boolean values); repeated ActiveModList entries; PackageName and dependencies; server rules; documented OS scope; minimum revision; and bounded log signals. `InstallRule.IsServer` must be a JSON boolean; the string `"true"` is rejected as malformed input. Output keeps recognized gameplay settings, package identifiers and next actions, rather than raw configs, passwords, IP addresses, local paths or raw log lines. The webpage provides a smaller configuration/manifest subset.

Paths are anchored to the actual executable directory. Official Workshop deployment and legacy manual UE4SS layouts must remain distinct. A provider's `Home/` is not a universal server root. Loader mentions do not prove that PalSchema, a child mod or a gameplay change loaded. No server connection, upload, edit, deletion or restart occurs.

## One fixed drop rate

```sh
python3 scripts/guide_tools.py odds --percent 3 --runs 100
```

Three percent is a supplied example, not a built-in item rate. This handles independent fixed outcomes without pity or dynamic rates. Use the conditional chain tool for multi-step acquisition.
