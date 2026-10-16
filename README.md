# Marginalia

A local CLI for revising Markdown with a terminal agent. The agent proposes; you review and approve; Marginalia checks and applies the change. No model SDK or API key is required. You can keep writing in Obsidian or another editor.

## Install and discover

Requires Python 3.12+ and uv, on Linux, WSL, or macOS. File locking currently uses POSIX facilities; native Windows is not supported.

```bash
uv sync
uv run marginalia
uv tool install --editable .
marginalia guide
marginalia guide tighten
```

Running `marginalia` shows commands. Each command has `--help`; `marginalia guide` contains the agent's editorial workflow. Topic guides cover structure, cleanup, tightening, compaction, translation, and review. A thin [agent skill](skills/marginalia/SKILL.md) routes to that authoritative guidance. Install or link its folder into your agent's skill directory to make it discoverable.

## Work through a pass

```bash
marginalia status draft.md --json
marginalia versions start draft.md --type tighten --brief 'Keep the examples and uncertainty.'
marginalia review schema
marginalia review submit draft.md --file proposal.json
marginalia review show draft.md p0001
marginalia review show draft.md p0001 --mode markdown
marginalia review accept draft.md p0001
marginalia versions finish draft.md
marginalia versions list draft.md
marginalia versions compare draft.md v0001
```

An agent prepares `proposal.json`, for example:

```json
{
  "kind": "replace",
  "original": "It is possible that this could help.",
  "replacement": "This could help.",
  "explanation": "Remove repeated hedging while retaining uncertainty.",
  "information_cuts": []
}
```

Submitting or revising a proposal does not change the draft. The author decides through the terminal conversation; the agent invokes `accept` only for an explicitly approved proposal. `reject` records an optional reason. `approve-cuts` records separate approval of declared substantive removals and does not itself apply text. Revising a proposal clears its cut approval. An `answer` to a query records clarification without changing the draft.

Targets must be exact, unique passages. Changed or ambiguous targets block acceptance; unrelated edits are retained. Target tracking is conservative: changing both surrounding contexts can make an unchanged passage outdated. Review it and submit a revised proposal rather than forcing acceptance. The CLI cannot prove semantic preservation or detect undeclared information cuts; the author and agent must inspect the actual wording.

Save unsaved editor changes and pause other writers before accepting or restoring. Marginalia serializes its own commands, checks disk text again before replacement, and keeps recovery copies. Its lock does not control Obsidian or another editor; unsaved buffers and an external writer racing the final check are outside that protection.

## Structure without rewriting

Use `marginalia guide structure` to agree on headings before reorganizing. An `insert` proposal adds a heading before an existing passage without replacing that passage. A `move` proposal relocates an unchanged exact passage before a unique destination anchor, retaining all its characters, links, and citations. Include the desired paragraph separators in the passage. An author query resolves ambiguous classification. Review shows moves as source and destination rather than disguising them as large rewrites.

The CLI provides literal terminal comparisons and plain-Markdown review output. An interactive diff picker, typed triggers, and an Obsidian interface are not implemented. Decisions are made through the agent conversation. Existing exploratory [issues](https://github.com/noah-art3mis/marginalia/issues) remain separate from this implementation.

## Versions and visible state

Versions is the command group for starting, resuming, and finishing passes, saving text, comparing versions, and restoring earlier drafts. A pass is the author-controlled traversal through a document; a version is saved text at a boundary. Restore saves current text first, interrupts the active pass, and marks pending proposals outdated. It preserves rejected and accepted decisions.

For `draft.md`, state is beside the document:

```text
.marginalia/draft.md/
  state.json
  proposals/p0001.json
  versions/v0001.md
  recovery/...
```

Versions contain only document text. JSON files contain pass and review state and are inspectable with ordinary tools. Do not edit workspace files while commands are running. Invalid state is reported; it is not silently reset. Leave an interrupted transaction journal and recovery files intact until the next command completes recovery or explains a conflict.

The brief is stored with its pass in `state.json`. Optional author-owned `brief.md`, `style.md`, and `notes.md` files inside the workspace are surfaced by `status`. Rejections remain in proposal files; exact rejected suggestions cannot be resubmitted in the same pass. Equivalent rewordings are not mechanically detected; agents consult previous decisions. A local rejection never automatically becomes a global style rule.

See [GLOSSARY.md](GLOSSARY.md) for domain terms, [AGENTS.md](AGENTS.md) for repository workflow, and [CODING_STANDARDS.md](CODING_STANDARDS.md) for review criteria.

## Development

```bash
uv run pytest -q --tb=short -x
uv run ruff check --quiet
uv run ruff format --check
```

Tests use synthetic drafts and exercise proposal acceptance, content-preserving moves, author edits, cut approval, versions, locking, and recovery. No real draft or paid model run is needed.

The [recorded agent forward test](tests/evidence/guide-forward-test.json) includes synthetic author requests, actual proposals and responses, CLI output, source hashes, and reproduction instructions. It checked that the candidate guides preserve uncertainty and withhold unapproved edits. It is an initial workflow check without a previous baseline or a cross-model editorial-quality claim.

## License

[MIT](LICENSE), copyright 2026 Gustavo Costa.
