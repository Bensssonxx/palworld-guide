# Gameplay workflows

Read the relevant section only. This is decision guidance, not a permanent game-stat database.

## Mining and handiwork

Distinguish working at a base from a party Pal used for manual resource gathering. Check unlocked buildings and the needed material. Compare acquisition route, suitability, partner/passive effects, then size, movement and food needs. Keep listed suitability, four-star values and global enhancements separate. A high work level does not prove an easy catch or measured throughput. Give a reachable current choice and a later upgrade when evidence supports them.

## Ground mounts

Read the current mount table through `pal_compare.py`. Compare ride sprint speed and stamina under the same conditions; stamina alone is not time and speed times stamina is not travel range. A technology-level filter is not a capture-level filter. Inspect the current mount and a small set of candidates for acquisition, saddle materials, jump/terrain behavior and partner effects before recommending one. Show tradeoffs rather than declaring every higher-level Pal better.

## Locations, dungeons and acquisition

Resolve the English name first. Keep game coordinates, provider record ID, category, nearest fast travel, retrieval time and source status. Use `map_tools.py` to plot sourced coordinates on real map tiles. A cave entrance, boss anchor, inside-chest location and mobile world event are different evidence types. Do not infer a fixed airdrop or spawn from a dynamic event. World Tree interiors and main-map coordinates need separate profiles.

## Loot chains, refreshes and farming

Identify item ID, quality, reward container, region, version, number of draws and whether a number is a probability or weight. A 100% entry applies only to its exact reward table. For camp → map → target routes, retrieve each conditional rate before using `farm_plan.py`. Account for time spent only on stages actually reached. Do not treat EnemyDropItemRate as a rare-drop probability multiplier.

Distinguish real time from game time, single-player from a continuously running server, camp resets from chest refreshes, and player observations from documented rules. Use `revisit` for an explicitly supplied interval, with the interval still labeled as reported/estimated. Suggest an observation to test uncertain timing; do not promise a fixed return time or restart a server.

## Items, combat and progression questions

Resolve the exact weapon, sphere launcher, ammunition, upgrade item or skill in its English article. Read its effect, ammo type and unlock requirements with `pal_compare.py entry` or the host browser. Separate player attack from Pal attack, equipment from permanent upgrades, and party capacity from base-worker limits. An item name alone cannot establish burst count, a special effect or cross-ammo compatibility. For sphere launchers, resolve homing versus scatter variants first: a tracking description establishes tracking, not the number of spheres consumed or emitted per trigger. Do not substitute magazine capacity for projectiles per shot. Where a mechanic remains uncertain, cite the missing field and recommend one in-game observation.

## Offline hunger, SAN and illness

First inspect the feed box: empty means reserves, production and transport are useful checks; food remaining points toward access, pathfinding or loading observations. Determine whether the server keeps running. Provider auto-pause settings require current provider instructions; do not guess panel labels. Check whether the panel overwrites file settings. Reducing hunger is separate from treating existing illness.

## Mods and dedicated servers

Resolve the full author page and package, client platform, server OS, game version and installation method. Similar titles can be different packages. Read PackageName, dependencies, InstallRule, IsServer and minimum revision. Steam subscription does not establish server deployment. Distinguish client-only, server-only and both-sides requirements using the author's statement rather than a mod's category name.

For 'I installed it but cannot see it', separate package deployment, activation, runtime loading and actual gameplay behavior. Inspect the latest launch, relevant deployment records and one observable effect. When a Workshop text fetch fails, use the host browser to inspect the author description and dependencies. Hidden page-template notices are not visible removal or compatibility warnings; verify the rendered state before making that claim.

Manual and Workshop loaders can be a duplicate-loading clue, not a proven crash cause. An access violation alone does not identify the responsible mod. Give one informative next check; live changes need separate scope and authorization.
