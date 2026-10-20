# Palworld Guide

[![CI](https://github.com/Bensssonxx/palworld-guide/actions/workflows/check.yml/badge.svg)](https://github.com/Bensssonxx/palworld-guide/actions/workflows/check.yml)

A local Agent Skill for sourced Palworld guidance: species breeding, material deficits, real-map marking, read-only server checks, and task-recorded web research fallback.

**Version:** 0.11.0-beta.2 (Beta). Fresh Codex CLI trials on macOS are recorded in [the Beta report](docs/INDEPENDENT_BETA.md); external-human and other-platform validation remain pending. The MIT license covers original adapter code and documentation; third-party/game data retains its own rights. See [notices](THIRD_PARTY_NOTICES.md) and [release status](docs/RELEASE_STATUS.md).

## Requirements

- Python 3.11 or newer. Core tools use the Python standard library; no `pip install` or API key is needed. The optional PNG exporter uses an already available Pillow/rsvg-convert environment and installs nothing.
- An assistant with file/terminal access. Automatic research fallback additionally requires that assistant's real search and page-reading tools. The standalone CLI cannot invent these capabilities.
- Network permission for public API/pages/map tiles. Species breeding works offline. Other offline operations need a populated, dated public cache. This public candidate omits saved community recipe/demo snapshots and bulk place labels.
- Codex is the primary installation target. Other Agent Skills hosts may load the files, but their installation and tool availability are not verified here.

## Install into a project

Clone the source (or download and extract its source archive), then install into an existing project:

```sh
git clone https://github.com/Bensssonxx/palworld-guide.git
cd palworld-guide
python3 tools/install.py --project /absolute/path/to/your/project
```

On Windows use `py -3` where `python3` is unavailable. The installer copies the skill into that project's `.agents/skills/palworld-guide`, preserves license notices, and refuses to replace an existing installation. It does not change your global skills, accounts or server. Open that project in Codex and invoke `$palworld-guide`. Local skill discovery follows the host's [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

Try:

```text
$palworld-guide
I have Bushi, Penking and Vanwyrm. How can I breed Pyrin?
```

Or ask for three coal clusters, supplying the travel points you have actually unlocked. The host reviews the task and uses the connected workflow; unsupported public questions produce research requests rather than fabricated game facts.

## Run directly

From this repository root:

```sh
python3 palworld-guide/scripts/workflow.py draft --question "I have Bushi, Penking and Vanwyrm; breed Pyrin" --output task.json
python3 palworld-guide/scripts/workflow.py run --task task.json --output-dir runs/first --offline
```

For online research, omit `--offline`. When the run returns `awaiting-research`, the assistant reads `research-queue.json`, performs actual searches and page reads, writes source-linked receipts, then resumes:

```sh
python3 palworld-guide/scripts/workflow.py resume --task task.json --previous-run runs/first/run.json --research receipts.json --output-dir runs/resumed
```

The user should not need to prepare receipts during a normal assistant session. If the host has no search/browser tools, the assistant must say so. Read [the task contract](palworld-guide/references/workflow.md) and [the research contract](palworld-guide/references/research.md).

## Data, privacy and limits

Public requests send game names/IDs and focused public queries. Roster/inventory arithmetic and supplied server-file analysis remain local. The bridge rejects obvious credential/private-path/IP patterns in search questions; this does not replace host privacy review. Keep actual tasks, profiles, receipts, logs, saves and cache files out of Git.

Breeding minimizes species dependency generations, not expected eggs or real time; check compatible individuals and setup. Materials are direct ingredients, not recursive raw-material expansion. Map clusters are geometric records, not measured yield, pathfinding or proven base sites. Only the main map is calibrated. Server checks never connect, install, edit or restart. Source disagreements, source-version limits and missing observations remain visible.

## Validate and build

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_release.py
python3 tools/build_release.py
python3 tools/beta_smoke.py
```

Outputs in `dist/` include an installable skill ZIP, a source ZIP, a file manifest and SHA-256 checksums. Rebuilding unchanged sources is deterministic. CI runs the unit tests, distribution checks, package build and clean installation smoke on Python 3.11/3.12/3.13 across Linux, macOS and Windows. Check the [Actions results](https://github.com/Bensssonxx/palworld-guide/actions) and [validation record](docs/VALIDATION.md) for the tested commit. Offline CI does not establish live-source availability, assistant answer quality or in-game correctness.

For bug reports, use the [template](docs/BETA_TESTING.md), with a public question and redacted results. Do not attach credentials, real saves or full private logs. There is no hosted chatbot or MCP service in this release.
