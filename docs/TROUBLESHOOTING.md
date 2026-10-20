# Troubleshooting

- **`awaiting-research`:** The task has reached the host search/browser handoff. The assistant should read the queue, perform actual searches/page reads, record receipts and resume. A terminal-only session cannot perform that host step automatically.
- **Offline cache missing:** Breeding records work offline; API/articles/map tiles need prior public cache. This public candidate excludes saved community recipe/demo snapshots. Retry online with the same reviewed task and a fresh output directory when authorized, preserving the failed run.
- **HTTP 429 or unavailable source:** Retain the failure and dated cache status. Use the host's supported browser/search fallback within its bounded budget; do not bypass access controls or claim a live fetch succeeded.
- **Invalid receipt:** Check request ID, real search events, read-page source IDs, excerpt hashes, timestamps and cited findings. Unresolved or no-result research must remain unresolved. Reusing a packet for a different task is rejected.
- **Missing coordinates/version/identity:** Obtain the required current player observation. Search cannot establish the player's position or actual deployed mod files.
- **Output already exists:** Choose a fresh run directory. Existing evidence and installations are preserved rather than overwritten.
- **Chinese text on Windows:** Files are explicitly UTF-8. Use Python 3.11+; `py -3 -X utf8` can also make the terminal/test environment consistent.
- **Map labels:** Chinese maps use known resource labels and neutral numbered point/travel labels for untranslated places; canonical source names remain in evidence. Bulk community place-label snapshots are omitted. Do not invent official translations. Only the main map is calibrated.
- **No skill appears:** Open the project you installed into, inspect `.agents/skills/palworld-guide/SKILL.md`, then refresh/restart the host if necessary. Other hosts need their own verified discovery path.

- **Blank terrain in a PNG conversion:** Some SVG renderers omit WebP without reporting failure. Open the original SVG in a modern browser, or use the documented optional `map_preview.py` exporter with an existing compatible environment. Inspect the actual output.
- **Research handoff rejected:** Preserve the rejected run, read its specific safe contract/audit reason, fix the receipt, and resume the unchanged task into a new output directory. Suggested queries are not proof of actual searches. Record all queries, open cited pages, and retain missing facts. A Codex trace gate is optional outside the recorded CLI Beta protocol.
