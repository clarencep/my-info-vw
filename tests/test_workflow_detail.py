"""Tests for workflow detail."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.workflows.check import InfoCheckWorkflow, CheckState, create_workflow


def test_check_state_creation():
    """Test CheckState creation."""
    state: CheckState = {
        "original_message": "test",
        "parsed": None,
        "queries": None,
        "search_results": None,
        "verification": None,
        "report": None
    }
    assert state["original_message"] == "test"


def test_workflow_graph():
    """Test workflow graph is created."""
    workflow = create_workflow()
    assert workflow.graph is not None


def test_workflow_nodes():
    """Test workflow has all nodes."""
    workflow = create_workflow()
    # Check that nodes are defined
    assert hasattr(workflow, "parser")
    assert hasattr(workflow, "query_generator")
    assert hasattr(workflow, "verifier")
    assert hasattr(workflow, "synthesizer")


def test_workflow_search_aggregator():
    """Test workflow has search aggregator."""
    workflow = create_workflow()
    assert hasattr(workflow, "search_aggregator")
    assert workflow.search_aggregator is not None
