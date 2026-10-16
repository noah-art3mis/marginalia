import pytest

from marginalia import proposals, versions
from marginalia.storage import MarginaliaError, Workspace


@pytest.fixture
def draft(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("# Start\n\nA long example with uncertainty.\n\n# End\n\nLast paragraph.\n")
    ws = Workspace(path)
    versions.start(ws, "tighten")
    return ws


def replacement(**kwargs):
    return dict(
        kind="replace",
        original="A long example with uncertainty.",
        replacement="An example, perhaps.",
        explanation="Tighter wording.",
        **kwargs,
    )


def test_review_does_not_write_and_accept_only_replacement(draft):
    original = draft.read_text()
    p = proposals.submit(draft, replacement())
    assert draft.read_text() == original
    assert "Tighter wording." in proposals.render(draft, p["id"], "markdown")
    assert "-A long example" in proposals.render(draft, p["id"])
    proposals.accept(draft, p["id"])
    assert draft.read_text() == original.replace(
        "A long example with uncertainty.", "An example, perhaps."
    )
    assert proposals.get(draft, p["id"])["status"] == "accepted"


def test_cut_approval_is_separate_and_revisions_reset_it(draft):
    p = proposals.submit(draft, replacement(information_cuts=["Removes uncertainty."]))
    with pytest.raises(MarginaliaError, match="cut"):
        proposals.accept(draft, p["id"])
    proposals.approve_cuts(draft, p["id"])
    proposals.revise(draft, p["id"], replacement(information_cuts=["Removes example."]))
    with pytest.raises(MarginaliaError, match="cut"):
        proposals.accept(draft, p["id"])
    proposals.approve_cuts(draft, p["id"])
    proposals.accept(draft, p["id"])


def test_unrelated_edits_survive_but_target_edits_are_outdated(draft):
    p = proposals.submit(draft, replacement())
    draft.document.write_text(draft.read_text() + "\nNew author ending.\n")
    proposals.accept(draft, p["id"])
    assert draft.read_text().endswith("New author ending.\n")
    other = proposals.submit(
        draft,
        dict(
            kind="replace", original="Last paragraph.", replacement="End.", explanation="Shorter."
        ),
    )
    draft.document.write_text(draft.read_text().replace("Last paragraph.", "Changed paragraph."))
    assert proposals.get(draft, other["id"])["status"] == "outdated"
    with pytest.raises(MarginaliaError, match="outdated"):
        proposals.accept(draft, other["id"])


def test_ambiguous_source_refused_and_rejections_survive_refresh(draft):
    p = proposals.submit(draft, replacement())
    proposals.reject(draft, p["id"], "Keep my voice.")
    with pytest.raises(MarginaliaError, match="rejected"):
        proposals.submit(draft, replacement())
    assert proposals.get(draft, p["id"])["reason"] == "Keep my voice."
    draft.document.write_text(draft.read_text() + "\nLast paragraph.\n")
    with pytest.raises(MarginaliaError, match="unique"):
        proposals.submit(
            draft,
            dict(
                kind="query", original="Last paragraph.", question="What?", explanation="Ambiguous."
            ),
        )


def test_move_preserves_exact_content_and_query_never_applies(draft):
    before = draft.read_text()
    source = "A long example with uncertainty.\n\n"
    p = proposals.submit(
        draft,
        dict(
            kind="move",
            original=source,
            destination="Last paragraph.",
            explanation="Place under end.",
        ),
    )
    shown = proposals.render(draft, p["id"])
    assert "Destination" in shown and source.strip() in shown
    proposals.accept(draft, p["id"])
    assert draft.read_text() == before.replace(source, "").replace(
        "Last paragraph.", source + "Last paragraph."
    )
    q = proposals.submit(
        draft,
        dict(
            kind="query",
            original="Last paragraph.",
            question="What does last mean?",
            explanation="Clarify.",
        ),
    )
    proposals.answer(draft, q["id"], "The conclusion.")
    unchanged = draft.read_text()
    with pytest.raises(MarginaliaError):
        proposals.accept(draft, q["id"])
    assert draft.read_text() == unchanged


def test_changed_source_does_not_attach_to_new_copy_elsewhere(draft):
    p = proposals.submit(draft, replacement())
    text = draft.read_text().replace("A long example with uncertainty.", "Revised example.")
    draft.document.write_text(text + "\nAppendix:\nA long example with uncertainty.\n")
    assert proposals.get(draft, p["id"])["status"] == "outdated"
    with pytest.raises(MarginaliaError, match="outdated"):
        proposals.accept(draft, p["id"])


def test_move_destination_edit_blocks_acceptance(draft):
    p = proposals.submit(
        draft,
        dict(
            kind="move",
            original="A long example with uncertainty.\n\n",
            destination="Last paragraph.",
            explanation="Move.",
        ),
    )
    draft.document.write_text(draft.read_text().replace("Last paragraph.", "New ending."))
    with pytest.raises(MarginaliaError, match="outdated"):
        proposals.accept(draft, p["id"])


def test_input_rejects_hidden_operations_and_absent_pass(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("Original.")
    ws = Workspace(path)
    with pytest.raises(MarginaliaError, match="pass"):
        proposals.submit(
            ws,
            dict(kind="query", original="Original.", question="Meaning?", explanation="Clarify."),
        )
    versions.start(ws, "clean up")
    with pytest.raises(MarginaliaError, match="Invalid proposal"):
        proposals.submit(
            ws,
            dict(
                kind="move",
                original="Original.",
                replacement="Dropped.",
                destination="Original.",
                explanation="Move.",
            ),
        )


def test_move_does_not_accept_a_noop(draft):
    original = "A long example with uncertainty.\n\n"
    with pytest.raises(MarginaliaError, match="already"):
        proposals.submit(
            draft,
            dict(
                kind="move", original=original, destination="# End", explanation="No actual change."
            ),
        )


def test_insert_adds_headings_without_replacing_body(draft):
    before = draft.read_text()
    p = proposals.submit(
        draft,
        dict(
            kind="insert",
            original="A long example with uncertainty.",
            replacement="## Examples\n\n",
            explanation="Add approved heading.",
        ),
    )
    assert draft.read_text() == before
    assert "Insert before" in proposals.render(draft, p["id"], "markdown")
    shown = proposals.render(draft, p["id"])
    assert "+## Examples" in shown
    assert "-A long example" not in shown
    proposals.accept(draft, p["id"])
    assert draft.read_text() == before.replace(
        "A long example with uncertainty.", "## Examples\n\nA long example with uncertainty."
    )


def test_diff_exposes_final_newline_changes(draft):
    p = proposals.submit(
        draft,
        dict(
            kind="replace",
            original="Last paragraph.",
            replacement="Last paragraph.\n",
            explanation="Add line boundary.",
        ),
    )
    shown = proposals.render(draft, p["id"])
    assert "\\ No newline at end of file" in shown
    assert "-Last paragraph." in shown and "+Last paragraph." in shown


def test_move_uses_approved_destination_even_if_removal_creates_a_new_match(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("aXYZb ... ab\n")
    ws = Workspace(path)
    versions.start(ws, "structure")
    proposal = proposals.submit(
        ws, {"kind": "move", "original": "XYZ", "destination": "ab", "explanation": "Move later."}
    )
    proposals.accept(ws, proposal["id"])
    assert path.read_text() == "ab ... XYZab\n"


def test_inspecting_large_unchanged_draft_does_not_run_quadratic_matching(tmp_path):
    from time import perf_counter

    path = tmp_path / "draft.md"
    paragraphs = [
        f"Section {n}: repeated wording and a distinct example {n}.\n\n" for n in range(350)
    ]
    path.write_text("".join(paragraphs))
    ws = Workspace(path)
    versions.start(ws, "tighten")
    proposal = proposals.submit(
        ws,
        {
            "kind": "replace",
            "original": paragraphs[175],
            "replacement": "A shorter section.\n\n",
            "explanation": "Tighten.",
        },
    )
    started = perf_counter()
    assert proposals.get(ws, proposal["id"])["status"] == "pending"
    assert perf_counter() - started < 1.0


def test_large_draft_with_unrelated_edit_still_reviews_promptly(tmp_path):
    from time import perf_counter

    path = tmp_path / "draft.md"
    paragraphs = [
        f"Section {n}: repeated wording and a distinct example {n}.\n\n" for n in range(350)
    ]
    path.write_text("".join(paragraphs))
    ws = Workspace(path)
    versions.start(ws, "tighten")
    proposal = proposals.submit(
        ws,
        {
            "kind": "replace",
            "original": paragraphs[175],
            "replacement": "A shorter section.\n\n",
            "explanation": "Tighten.",
        },
    )
    path.write_text(path.read_text() + "Unrelated author addition.\n")
    started = perf_counter()
    assert proposals.get(ws, proposal["id"])["status"] == "pending"
    assert perf_counter() - started < 1.0


def test_adding_a_new_paragraph_keeps_a_single_paragraph_proposal_usable(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("It could possibly help.\n")
    ws = Workspace(path)
    versions.start(ws, "tighten")
    proposal = proposals.submit(
        ws,
        {
            "kind": "replace",
            "original": "It could possibly help.",
            "replacement": "It could help.",
            "explanation": "Tighten.",
        },
    )
    path.write_text(path.read_text() + "\nA new paragraph.\n")
    proposals.accept(ws, proposal["id"])
    assert path.read_text() == "It could help.\n\nA new paragraph.\n"


def test_move_revalidates_nonoverlap_after_author_changes_separators(tmp_path):
    path = tmp_path / "draft.md"
    path.write_text("ABC\n\nBCD")
    ws = Workspace(path)
    versions.start(ws, "structure")
    proposal = proposals.submit(
        ws,
        {
            "kind": "move",
            "original": "ABC",
            "destination": "BCD",
            "explanation": "Move the first passage after the separator.",
        },
    )
    path.write_text("ABCD")
    with pytest.raises(MarginaliaError, match="overlap"):
        proposals.accept(ws, proposal["id"])
    assert path.read_text() == "ABCD"
