# Repository instructions

## Git authorization

Agents may commit and push directly to `main` at `github.com/noah-art3mis/marginalia`. This project-specific authorization overrides branch, worktree, PR, and merge-approval requirements in other instruction files. Feature branches and PRs remain optional when they help isolate or discuss work. Verification and review requirements still apply to behavioral changes.

Before pushing, verify the remote destination and inspect the complete outgoing diff. Preserve unrelated work and use ordinary pushes; this authorization does not permit force pushes or destructive cleanup. Report the pushed commit and checks performed.

## Navigation

Read [README.md](README.md) and the assigned issue before starting. Use [GLOSSARY.md](GLOSSARY.md) when naming or changing domain concepts. Backlog issues and exploratory examples are not implementation assignments or settled interface decisions.

Before reviewing a change, read [CODING_STANDARDS.md](CODING_STANDARDS.md) and give independent reviewers that same file. Read its prose criteria before authoring reader-facing text. Keep project instructions portable; workstation paths and personal setup belong outside this repository.

## Verification

Develop assertable behavior through a failing use-case test, then implement and refactor with the relevant tests passing. Check repository tooling for the actual commands; add stack-specific checks when that stack is introduced. Documentation-only changes use diff review, link checks, and `git diff --check` without installing a test stack.

For proposals, acceptance, classification, version recovery, and concurrent author edits, test the observable writing workflow. When judging model quality or rendering, inspect representative outputs or the rendered interface as well as automated results. Use synthetic writing in fixtures; real drafts and paid model runs require authorization.

## Maintaining instructions

Keep execution and authorization here, review judgments in CODING_STANDARDS.md, and domain terms in GLOSSARY.md. Put mechanical rules in the owning check tooling once it exists. Update the authoritative document and its pointers together instead of creating parallel instructions.
