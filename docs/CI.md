# Remote CI verification — 2026-10-20

Repository: [Bensssonxx/palworld-guide](https://github.com/Bensssonxx/palworld-guide), public. GitHub identifies the root license as MIT.

The initial published source commit [`60eda7a71101256cc0271075bb1c699d2f8cf6c0`](https://github.com/Bensssonxx/palworld-guide/commit/60eda7a71101256cc0271075bb1c699d2f8cf6c0) passed [Actions run 39482784465](https://github.com/Bensssonxx/palworld-guide/actions/runs/39482784465). All nine matrix jobs completed successfully on the first attempt:

| Hosted runner | Python 3.11 | Python 3.12 | Python 3.13 |
|---|---|---|---|
| ubuntu-latest | Passed | Passed | Passed |
| macos-latest | Passed | Passed | Passed |
| windows-latest | Passed | Passed | Passed |

Each job runs the 70-test offline suite, bounded source/distribution checks, deterministic package build and a fresh-installation smoke test. No CI failure required a code repair. The smoke test's research receipt is explicitly synthetic; it does not claim a real web search.

This record is added in a documentation-only follow-up commit. Runtime scripts, data, tests and the workflow are unchanged from the verified source commit. The follow-up commit triggers its own matrix; [Actions](https://github.com/Bensssonxx/palworld-guide/actions) and the README badge show the latest result.

Hosted-runner success establishes execution of these offline checks in the matrix environments. It does not establish live API availability, other assistant-host compatibility, end-user feedback, in-game correctness, map terrain suitability or live server administration. The separate fresh-model Beta trials remain macOS-only; see [the Beta report](INDEPENDENT_BETA.md).
