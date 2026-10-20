# Beta test protocol and feedback

Use a fresh project and a fresh assistant conversation. Install using only the README. Avoid the author's original workspace, caches, player files and chat history. The host needs terminal/file access and public search/page-reading tools; record their actual availability.

Run at least: an owned-species breeding request; a material query with supplied stock; a main-map resource query; a missing-coordinate request; an unsupported public question that queues search; and an article query that fails then resumes with evidence. Include Chinese/English variants if supported by the chosen host. Confirm that research queries omit private data, pages are actually read, source limitations survive, and dependent steps resume without inventing unknown values.

Record separately: installation success, time to first useful result, correct tool/argument selection, source relevance, actual map readability, task continuation, and unresolved questions. A clear partial answer can be correct; a fabricated certainty is a failure. Tool test totals are not a substitute for this trial.

## Feedback template

- Candidate version and archive checksum:
- OS / Python / assistant host and model:
- Terminal, search and browser capabilities available:
- Exact public question and synthetic player context:
- Expected behavior:
- Actual behavior and redacted task/run step IDs:
- Supporting public URLs and map screenshot, if shareable:
- Was a missing observation or unsupported fact guessed?
- Reproduction steps:

Do not include passwords, tokens, IP addresses, private paths, full logs, real save files or raw application materials. No invitations/messages are sent automatically. See INDEPENDENT_BETA.md for completed fresh CLI trials; external-human and other-host results remain pending.

For recorded Codex CLI trials, provide a per-question JSONL tool trace and use `--host-trace` on resume. Include exploratory searches and failed reads in total budgets; inspect full-page result records because a batched open can be labelled with only its first URL or `other`. Do not copy account configuration, chat text or traces into the public package. Account reuse must remain local and private; fresh CLI trials on one computer do not establish VM-level isolation or cross-platform support.
