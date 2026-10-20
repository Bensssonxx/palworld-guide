# Fresh-session Beta — 2026-10-20

Historical trial candidate: `0.11.0-beta.2`. Subsequent public upload and hosted-runner CI are recorded in [release status](RELEASE_STATUS.md) and [CI evidence](CI.md). Six fresh Codex CLI conversations exercised three question families, with repairs and repeats. These are six sessions, not six independent users or a broad gameplay-accuracy benchmark.

## Environment and independence

Source ZIPs were extracted outside the author's application workspace and installed using only `tools/install.py`. New projects, home/config directories and empty public caches were used. No author QA or previous chat was supplied. Recovery trials intentionally received saved task/run/receipt files and a private tool trace, without the prior conversation. Observed commands contained no reads of the original application workspace, memories or login files.

Host: Codex CLI `0.163.0-alpha.10.2`, macOS. The CLI selected its default model; the collected stream does not identify the concrete model, so no cross-model claim is made. Memories, apps and plugins were disabled in the test configuration. Existing account login was reused privately and locally; temporary login copies were removed after the runs. This is same-machine process/configuration separation, not a VM or a filesystem-security isolation claim. No MCP service, dependency installation, game/server change, external invitation or publication occurred.

## Actual rounds

| Round | Public question / checkpoint | Result |
|---|---|---|
| Map baseline | Five Chinese ore locations, coordinates, a real map; clarify base recommendation | Delivered map; exposed base-intent misclassification, Chinese assumption-check false positive, untranslated place labels and WebP rasterizer limitations |
| Search baseline | Steam/Xbox/PS5 dedicated-server support, settings and password restrictions | Useful answer, but not accepted as a clean handoff: public password topic was initially blocked, five actual queries exceeded the three-query budget, and a historical-page receipt lacked a page read |
| Weapon recovery | Resume a saved failed launcher field lookup; ask exact firing count and schematic acquisition | Continued without the old chat or rerunning the initial lookup. Corrected rejected source lineage. Acquisition guidance delivered; exact per-trigger count remains unverified and partial |
| Search repair trial | Same server question with trace auditing enabled | Exposed missing discovery lineage, generic diagnostics and batched-open trace format differences; rejected attempts preserved |
| Cross-session recovery | New installation/conversation receives that rejected server task and saved evidence | Repaired receipt; real trace audit matched **3 queries / 5 page reads**. Password/platform details and supplied-version limits remain explicitly partial |
| Map final | New home/project/cache; repeat the Chinese ore question | Correct draft, real online data, documented PNG exporter, Chinese labels, actual image inspection, coordinates/source links and final delivery check passed |

The final map host reviewed raw nodes and selected clusters as an explicit, adjustable interpretation of distinct destinations; it preserved the initial run. The radius is 40 coordinate units. Counts are distinct source coordinates, not measured ore yield, physical node counts, safe routes or base feasibility.

## Repairs

- Public password questions and configuration names are allowed; supplied nonempty credential values remain blocked.
- Base disclaimers no longer imply a base-selection request. Common Chinese default-disclosure wording is recognized.
- Chinese maps keep untranslated canonical names in evidence and use neutral numbered labels in display.
- The optional PNG exporter converts embedded WebP before rasterization, rejects active/external SVG input and preserves originals. It requires existing Pillow and `rsvg-convert`; core tools remain standard-library Python.
- Optional CLI trace auditing checks every actual query, returned source URL, full-page result and operation budget. It supports batched results, including batches labelled with only their first URL. This does not authenticate logs, excerpts, timestamps or source truth.
- Receipt failures expose safe specific contract reasons. Missing article fields retain available sections and a bounded overview. Weapon and server questions get relevant source hints; cross-platform server questions route to research.

## Validation and limits

The curated public tree passes **70 Python tests**; the maintained development tree passes **107**. Counts describe different suites and are not additive gameplay trials. Final archives also receive the clean-interpreter installation smoke test, including offline species planning and a clearly synthetic receipt fixture. The optional PNG exporter was actually exercised with existing Pillow 11.1.0 and rsvg-convert; final images were visually inspected.

One final trace-counter repair occurred after the fresh CLI recovery run: a batch labelled `open_page` can contain multiple page results. The actual preserved trace was re-audited with the corrected counter and passes at 3 queries / 5 reads; a regression test covers this shape. Documentation and packaging were finalized afterward. This is not a claim that every final archive byte underwent another fresh-model trial.

Exact launcher projectiles per trigger and console-specific password behavior remain unresolved. Some inherited server excerpts/timestamps were not independently reread; the resumed answer labels that limitation. Page-open auditing proves logged operations, not whether all statements follow from the pages. The host still reviews semantics, compound coverage, map appearance and player feasibility. A source-order node list may need an explicit cluster interpretation to describe distinct destinations.

At the time of these fresh CLI trials, no external-human feedback, different assistant host, Windows/Linux execution, remote GitHub Actions or in-game/server validation had been established. Subsequent [remote CI](CI.md) establishes offline script/package execution on its matrix runners; the other limitations remain. The owner has since confirmed the public destination and MIT license; the candidate is suitable for controlled Beta distribution; it is not a stable release or universal answer guarantee. Detailed raw QA stays local and is excluded from this repository/package.
