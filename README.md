# Marginalia

Revise Markdown drafts with Codex in a terminal while you read and write in Obsidian. Codex proposes changes, you discuss them, and Marginalia applies only the proposals you approve. It also saves versions so you can compare passes and recover earlier text.

Marginalia runs locally. It has no chat window or Obsidian plugin and requires no separate model API key. You use your existing terminal agent.

## Your first editing pass

If Marginalia is installed, open Codex in a terminal and give it the path to your note. Save the note in Obsidian first. For example:

> Use Marginalia on `/path/to/vault/Essays/draft.md`. Start a tightening pass. Keep the examples and uncertainty. Propose a change to the first paragraph and show me before changing anything.

Codex uses Marginalia to save the starting text and prepare a proposal. Read the original, suggested replacement, and explanation in the terminal. Then reply naturally:

- “Keep the example. Try again with a smaller change.”
- “Accept this proposal. Next paragraph.”
- “Reject this one. Keep my wording.”
- “Pause here. We’ll continue later.”

You do not need to write proposal JSON or remember acceptance commands. Codex handles those operations in response to your decisions. Asking a question or discussing a suggestion does not approve it. Proposed information cuts, such as dropping an example or qualification, need separate approval.

Save your Obsidian edits and pause typing before asking Codex to apply a proposal or restore a version. Marginalia checks the text saved on disk; it cannot see unsaved editor text or lock Obsidian. If the target passage has changed or become ambiguous, acceptance is blocked so you can request a fresh proposal. Edits elsewhere are retained.

When you have gone through the document, say:

> Finish this pass and show me what changed from the starting version.

A **pass** is your traversal through the draft for a purpose, such as tightening or translating. A **version** is a saved copy of the text. Starting a pass saves the starting version; finishing saves the result. You can pause and resume a pass without starting over.

## Remember your vault and note names

Store local settings as plaintext files instead of repeating long paths. Run these commands from your vault folder, or ask Codex to set them up there:

```bash
cd /path/to/vault
marginalia config set vault /path/to/vault
marginalia config set obras 'Essays/draft.md'
marginalia config show
marginalia status @obras
```

`obras` is a name you choose for the note. You can then tell Codex:

> Use Marginalia on `@obras`. Resume our tightening pass and show me the next proposal.

The settings live in `.marginalia/config.json`. Marginalia finds that file by looking in the terminal's current folder and its parent folders. Start Codex from that folder or a child folder to use the saved names; they are not global shortcuts.

Relative note paths in these settings are resolved against `vault` when it is set, otherwise against the folder containing `.marginalia`. Ordinary document paths still resolve against the terminal's current folder. Any command that takes a document path also accepts `@obras` or another saved name.

Use `marginalia config unset obras` to remove a name. These are Marginalia settings, not shell environment variables.

## Other things you can ask for

For a rough draft, begin with structure:

> Propose headings for this draft. After I approve them, suggest where each passage belongs. Keep the wording unchanged and ask me about ambiguous placements.

Codex can propose headings and moves separately. Marginalia moves the exact passage, including its links and citations. Review shows its source and destination rather than presenting the move as a rewrite.

For later passes, ask for cleanup, tightening, compaction, or translation and explain what must be preserved. You control the scope and pace; choosing a pass type does not authorize a whole-document rewrite.

To revisit earlier work, ask:

> Show the saved versions and compare the current draft with the start of the last pass.

Restoring a version saves the current text first, interrupts the active pass, and marks pending proposals outdated. Accepted and rejected decisions remain recorded. The CLI checks text preservation for moves, but it cannot determine whether a rewrite changes meaning or contains an undeclared information cut. Read the proposal before approving it.

## Where your files live

Your draft stays an ordinary Markdown file. For `Essays/draft.md`, Marginalia stores its review state and saved text beside it:

```text
Essays/
  draft.md
  .marginalia/
    draft.md/
      state.json
      proposals/p0001.json
      versions/v0001.md
      recovery/...
```

Versions contain only document text. Pass details and review decisions are stored in inspectable JSON files. Optional `brief.md`, `style.md`, and `notes.md` files inside the document workspace hold author-owned context; `marginalia status` shows their contents and the workspace location.

The folder settings file is separate from each document's workspace. If you configure Marginalia from your vault folder, settings and document workspaces are both within the vault. If you configure it from a different terminal project folder, its settings stay there while each document's versions and proposals stay beside that document.

Do not manually edit state while a command is running. Invalid state produces an error rather than being silently reset. Keep recovery files and any interrupted transaction journal intact until Marginalia completes recovery or explains a conflict.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/), on Linux, WSL, or macOS. Native Windows is not supported; on Windows, run Marginalia and Codex inside WSL.

From this repository:

```bash
uv tool install --editable .
marginalia
marginalia guide
```

The bundled [agent skill](skills/marginalia/SKILL.md) tells Codex to load Marginalia's workflow guidance. Install or link its folder into your agent's skill directory. If the skill is not available in a session, tell Codex to run `marginalia guide` before working on your draft.

## Commands when you need them

Running `marginalia` shows the available commands. Each command has `--help`. The bundled guides explain the editorial workflow:

```bash
marginalia guide
marginalia guide structure
marginalia guide tighten
marginalia guide review
```

You can also inspect state directly:

```bash
marginalia status @obras
marginalia review list @obras
marginalia review show @obras p0001
marginalia review show @obras p0001 --mode markdown
marginalia versions list @obras
marginalia versions compare @obras v0001
```

Proposal commands support terminal comparisons and plain-Markdown review output. Decisions happen through your agent conversation. An interactive diff picker and typed triggers are not implemented. The exploratory [issues](https://github.com/noah-art3mis/marginalia/issues) describe possible additions.

For tool integrations, `marginalia review schema` describes proposal inputs. Many state commands offer `--json` output. Normal author use does not require preparing those files manually.

## Development

```bash
uv sync
uv run pytest -q --tb=short -x
uv run ruff check --quiet
uv run ruff format --check
```

Tests use synthetic drafts and exercise proposal acceptance, content-preserving moves, author edits, cut approval, versions, locking, and recovery. No real draft or paid model run is needed.

The [recorded agent forward test](tests/evidence/guide-forward-test.json) includes synthetic author requests, actual proposals and responses, CLI output, source hashes, and reproduction instructions. It checked that the candidate guides preserve uncertainty and withhold unapproved edits. It is an initial workflow check without a previous baseline or a cross-model editorial-quality claim.

The [structural conversation replay](tests/evidence/structure-guide-replay.json) compares baseline and candidate guides using [reusable synthetic cases](tests/fixtures/guide-conversation.json). It checks before/after outlines, technical register, authorized heading changes and passage moves, editor conflicts, and the existing uncertainty-preservation cases. The record includes actual responses, operations, source hashes, results, and evaluation limits; it does not establish behavior across models or in a live editor.

See [GLOSSARY.md](GLOSSARY.md) for domain terms, [AGENTS.md](AGENTS.md) for repository workflow, and [CODING_STANDARDS.md](CODING_STANDARDS.md) for review criteria.

## License

[MIT](LICENSE), copyright 2026 Gustavo Costa.
