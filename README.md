# Marginalia

Obsidian toolkit for AI-assisted Markdown editing, with reviewable changes and versioned drafts.

Marginalia is in the design stage. There is no installable plugin yet. Follow the [design and feature issues](https://github.com/noah-art3mis/marginalia/issues) for current work.

## Intended workflow

1. Start with a large, loosely structured Markdown draft. Ask an agent to propose headings, then classify and move existing passages beneath the agreed headings without rewriting their content.
2. Choose an editing pass, such as cleanup, tightening, compaction, or translation. Add a short editorial brief describing the intended voice, permitted changes, and content to preserve.
3. Work through the document at your own pace. The agent proposes changes; you inspect, discuss, accept, or reject them. Planned review modes include plain-Markdown proposals and an interactive diff.
4. Use Versions to start, resume, or finish a pass, compare saved text, and recover earlier text. Save recoverable document text at author-controlled pass boundaries.

A paragraph rewrite can be one proposal accepted or rejected as a whole. Accepting a proposal and then editing the resulting text is sufficient. Removing substantive information, including examples and qualifications, requires explicit approval separate from accepting wording changes.

## Design commitments

- Preserve the author's wording during classification and reorganization.
- Keep proposed changes observable and require approval before applying them.
- Detect when a proposal's target passage has changed rather than overwriting newer writing.
- Preserve editorial decisions when suggestions refresh. A local rejection does not silently become a permanent style rule.
- Make the editorial brief, optional style sheet, decision memory, and other project context visible and accessible to both the author and agent tools.
- Keep saved document versions limited to document text, separate from proposals and review metadata.

Typed paragraph triggers, Markdown blockquotes, and Obsidian callouts are interaction ideas to explore. Their syntax and implementation are not settled. An external coding agent in a terminal is a valid integration direction; an embedded chat interface is not required.

See the [glossary](GLOSSARY.md) for domain terms. Architecture, storage format, and the initial prototype remain open design decisions.

## Contributing

Read [AGENTS.md](AGENTS.md) for repository workflow and Git authorization, and [CODING_STANDARDS.md](CODING_STANDARDS.md) for review criteria.

## License

[MIT](LICENSE), copyright 2026 Gustavo Costa.
