# Marginalia coding standards

These are project-specific review judgments. Cite the affected behavior and a concrete consequence when reporting a finding. Execution and Git authorization live in [AGENTS.md](AGENTS.md); domain definitions live in [GLOSSARY.md](GLOSSARY.md).

## Author control and information preservation

Evaluate a change against the author's requested pass and editorial brief. A polished rewrite can still fail by changing meaning, voice, uncertainty, examples, or qualifications. Treat unexplained omissions and unapproved information cuts as substantive failures.

Classification and reorganization must preserve body content while changing placement under approved headings. Assess passage boundaries, links, citations, and ambiguous placement as part of that contract. Text conservation can be checked mechanically; whether an edit preserves meaning still requires reading the actual source and proposal. An agent's assertion that it retained all information is not evidence by itself.

## Proposal clarity and review scale

The author should be able to tell what will change, why it was proposed, and what accepting it will do. Keep replacement content, explanations, author queries, and information-cut notices distinguishable. Judge the resulting document as well as the displayed diff: commentary must not become accepted prose.

Match presentation to the operation. A paragraph rewrite needs readable local comparison; a structural move needs source, destination, and unchanged content. A large delete-and-insert diff can obscure the nature of a move. Plain-Markdown and interactive review should express the same pending proposal and decision.

Acceptance followed by ordinary editing satisfies the initial replacement-editing workflow. Assess extra controls against a demonstrated author need rather than adding them to imitate a full word processor.

## Concurrent writing and recovery

Read acceptance, rejection, refresh, undo, and restore as complete user operations. A proposal must not silently replace newer author wording. Unrelated edits should leave the proposal usable; changed target text needs an understandable outdated state and a way forward.

Assess version recovery independently from proposal state and discussions. Saved versions contain document text. Restoring or refreshing should not silently lose writing, resurrect rejected proposals, or imply approvals the author did not give. Check the outcome after interruption and failure, not just the success path.

## Visible editorial context

The brief, style sheet, and decision memory should be understandable, discoverable, and correctable by the author. Agent tools should use the same authoritative context as the review interface. Report hidden duplicate memory or inconsistent scope with an example of the differing suggestions it could cause.

Distinguish passage-specific rejection from a project-wide preference. Reconsidering a decision after meaningful text or scope changes should expose the previous decision; refreshing alone should not pressure the author with the same rejected advice.

## Boundaries and security

Keep proposal meaning and decisions independent of Markdown rendering, the Obsidian adapter, and the chosen model provider. Review whether those boundaries let an external agent participate without a second implementation of the writing workflow. Use existing facilities when they satisfy the contract; justify a new abstraction with the responsibility it owns.

Treat model output and imported Markdown as untrusted input. Consider the actual renderers, executable extensions, file operations, and tool permissions reached by a feature. Review the resulting authority and data exposure, rather than relying on a generic claim that a preview is read-only.

## Reading and interaction

Inspect the complete sequence of requesting, reading, deciding, and returning to writing. Typed triggers and shortcuts should preserve focus, reading position, and ordinary text entry. Explain pending work and outdated proposals without making the author navigate implementation details. Distinguish proposed syntax from a settled interaction.

Use rendered evidence when readability, focus, or movement is the contract. Motion should explain a passage's movement or preserve orientation; it should remain optional for users who reduce motion. Prefer existing Markdown and Obsidian conventions when they keep the proposal readable in both source and rendered views.

## Tests and evidence

Favor tests through stable writing operations over assertions about internal call order or serialized display details. Each test should protect a named failure, such as an unseen overwrite, lost passage, stale acceptance, or rejected suggestion returning on refresh. Mechanical checks enforce syntax and wiring; review judges whether the behavior and presentation serve the author.

For model or prompt changes, inspect representative proposals for omissions, unsupported additions, and compliance with the pass brief. State the tested entry point, fixtures, settings, and limits of the evidence. A schema-valid response or green aggregate score does not establish editorial quality.

## Documentation and prose

Keep one authoritative explanation per concern and make it reachable from the README or the relevant owning document. Describe implemented behavior separately from intended workflow and unresolved design choices. Update conflicting descriptions in the same change.

Write concrete sentences that add a decision, fact, consequence, or instruction. Remove introductions that merely repeat a heading or advertise quality. Preserve qualifications that affect meaning. Keep Markdown paragraphs on single source lines and choose examples that clarify the author's task.
