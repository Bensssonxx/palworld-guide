# GitHub upload preparation

This standalone repository is now public at [Bensssonxx/palworld-guide](https://github.com/Bensssonxx/palworld-guide), with the owner-confirmed MIT license. [CI evidence](CI.md) records the first successful nine-job matrix. The checklist below remains useful for subsequent source uploads. Never upload the parent application workspace. Local checks do not create tags, releases or invitations.

## Before a source upload

1. Owner-confirmed destination (2026-10-20): `Bensssonxx/palworld-guide`, public.
2. Owner-confirmed license (2026-10-20): MIT for original code/documentation; retain `THIRD_PARTY_NOTICES.md`. Game assets and independent providers keep their own rights.
3. Read `docs/INDEPENDENT_BETA.md`, `docs/RELEASE_STATUS.md` and the final source diff. Keep local host traces, account configuration, player records, public caches and generated maps outside the public tree.
4. Run the commands below and inspect the resulting file manifest. Upload only after explicit authorization for the chosen destination.

```sh
python3 -m unittest discover -s tests -v
python3 tools/check_release.py
python3 tools/build_release.py
python3 tools/beta_smoke.py
git status --short
```

Use the user's existing configured Git identity for reviewed commits; do not invent an author identity. Do not include `dist/` or private test logs in Git. A prerelease may attach the two generated ZIPs and `SHA256SUMS` after their hashes are checked.

## Verify after upload

Run the existing read-only GitHub Actions matrix and inspect every OS/Python job before claiming platform support. Fix failures before a public prerelease tag. The hosted CI now establishes offline test/build/install execution on Windows, Linux and macOS. Other assistant hosts, external human feedback and in-game validation remain separate evidence.

Suggested initial prerelease label: the exact value in `VERSION`. Release notes should describe local tools, host-assisted search, optional trace auditing, known partial answers and map/browser requirements. Do not market this as a hosted chatbot, an MCP service or a source-truth guarantee.
