from importlib.resources import files

import pytest
from typer.testing import CliRunner

from marginalia.cli import app

runner = CliRunner()


def test_default_guide_exposes_bundled_workflow_without_requiring_a_document():
    result = runner.invoke(app, ["guide"])

    assert result.exit_code == 0, result.output
    workflow = files("marginalia").joinpath("guides", "workflow.md").read_text()
    assert result.stdout.strip() == workflow.strip()


@pytest.mark.parametrize(
    "topic",
    ["structure", "tighten", "compact", "cleanup", "translate", "review", "verify", "dedupe"],
)
def test_each_workflow_topic_is_accessible_to_an_external_agent(topic):
    result = runner.invoke(app, ["guide", topic])

    assert result.exit_code == 0, result.output
    guide = files("marginalia").joinpath("guides", f"{topic}.md").read_text()
    assert result.stdout.strip() == guide.strip()


def test_unknown_topic_reports_available_guides_instead_of_a_traceback():
    result = runner.invoke(app, ["guide", "imaginary-pass"])

    assert result.exit_code != 0
    assert "structure" in result.output
    assert "review" in result.output
    assert "Traceback" not in result.output
