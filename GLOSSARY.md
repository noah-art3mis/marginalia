# Glossary

Terms for an author revising a document through deliberate passes with an agent's assistance.

## Language

**Pass**:
One author-controlled traversal from the start of a document to its finish, also called an iteration. The author may stop and resume during the pass. A pass describes the editing work; a saved version preserves document text at a boundary of that work.
_Avoid_: Generation, message, individual edit

**Proposal**:
An agent's suggested change that the author can inspect and discuss before deciding whether it becomes part of the document. A paragraph rewrite may form one proposal accepted or rejected as a whole.
_Avoid_: Applied edit, automatic rewrite

**Pass type**:
The purpose guiding a pass, such as compacting, tightening, translating, or cleaning up. The author directs the agent’s edits during the pass.

**Information cut**:
A proposed removal of a claim, example, qualification, uncertainty, or other substantive content. It requires explicit approval distinct from accepting wording changes.
_Avoid_: Shortening, redundant wording

**Review mode**:
The way the author inspects and decides on proposed changes. Required modes include plain-Markdown suggestions and interactive diff review.

**Structuring stage**:
The work of agreeing on headings and placing passages under them before prose editing begins. Passages may be split and moved while their wording is preserved.

**Move proposal**:
A proposed relocation of an unchanged passage from its current position to a destination in the agreed outline. The author can inspect the passage and decide whether to accept the move.

**Saved version**:
A recoverable copy of the document text associated with a pass boundary. It does not include proposals, discussions, or review decisions. Versions is the user-facing command group for starting, resuming, and finishing passes, comparing saved text, and recovering earlier text; passes do not need a separate command group.

**Outdated proposal**:
A proposal whose target passage has changed since it was prepared. It needs review or regeneration before acceptance; edits elsewhere do not make it outdated.

**Author query**:
A question attached to a passage that asks the author to clarify meaning or make an editorial decision. It can exist without a proposed replacement, and answering it does not by itself approve a text change.

## Editorial context

**Editorial brief**: A short, author-editable description of a pass's purpose, audience, scope, voice, permitted intervention, and protected content. It supplements the pass type and does not authorize automatic edits.

**Style sheet**: An optional record of explicit terminology, spelling, capitalization, citation, and other consistency choices. Rejecting a proposal does not automatically add a style rule.

**Decision memory**: A concise, inspectable record of editorial decisions used to keep refreshed suggestions and agent sessions from repeatedly proposing rejected changes. A local rejection is distinct from a project-wide rule.

**Typed trigger**: A text marker used to request an agent action on a passage without a picker or mouse interaction. The proposed example is !! before a paragraph; the syntax and dispatch behavior remain unsettled.
