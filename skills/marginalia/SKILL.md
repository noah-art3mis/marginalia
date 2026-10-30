---
name: marginalia
description: Use Marginalia to structure or revise Markdown drafts through author-reviewed proposals and recoverable versions. Use when the user requests Marginalia or a proposal-based editing pass.
---

Run `marginalia guide` for the authoritative workflow, then `marginalia status DOCUMENT --json` for the current pass, proposals, versions, and editorial context. Read the relevant topic with `marginalia guide TOPIC`; use command help and `marginalia review schema` for supported operations and input formats.

Follow the author's requested scope and decisions through that workflow. The bundled guide owns editorial instructions; keep this entry point thin.

The author's first pass on a draft is a cleanup that also fills placeholders: a bracketed reference such as `[text as data]`, a bare `...` or `Example ...`, a `**[Table N: ...]**` marker, or a link left empty gets a researched replacement proposal that names its source in the explanation, so the author accepts filled text instead of answering a query. Record that scope in the pass brief when starting.
