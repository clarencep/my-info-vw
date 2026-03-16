"""Tests for workflow module."""

import pytest
from dotenv import load_dotenv

load_dotenv()


def test_workflow_import():
    """Test workflow can be imported."""
    from src.workflows.check import InfoCheckWorkflow, create_workflow
    assert InfoCheckWorkflow is not None
    assert create_workflow is not None


def test_workflow_creation():
    """Test workflow can be created."""
    from src.workflows.check import create_workflow
    workflow = create_workflow()
    assert workflow is not None
    assert hasattr(workflow, "run")
    assert hasattr(workflow, "graph")


def test_workflow_should_verify_with_results():
    """Test _should_verify returns 'verify' when search has results."""
    from src.workflows.check import InfoCheckWorkflow

    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "test",
        "parsed": {},
        "queries": [],
        "search_results": [{"title": "result1", "url": "http://example.com"}],
        "verification": None,
        "report": None
    }
    result = workflow._should_verify(state)
    assert result == "verify"


def test_workflow_should_verify_without_results():
    """Test _should_verify returns 'skip_verify' when search has no results."""
    from src.workflows.check import InfoCheckWorkflow

    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "test",
        "parsed": {},
        "queries": [],
        "search_results": [],
        "verification": None,
        "report": None
    }
    result = workflow._should_verify(state)
    assert result == "skip_verify"


def test_workflow_should_verify_with_none_results():
    """Test _should_verify returns 'skip_verify' when search_results is None."""
    from src.workflows.check import InfoCheckWorkflow

    workflow = InfoCheckWorkflow()
    state = {
        "original_message": "test",
        "parsed": {},
        "queries": [],
        "search_results": None,
        "verification": None,
        "report": None
    }
    result = workflow._should_verify(state)
    assert result == "skip_verify"
