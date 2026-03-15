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
