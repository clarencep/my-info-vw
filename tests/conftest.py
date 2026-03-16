"""Pytest configuration."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# In CI (no real API keys), set a dummy key so LLMManager can initialize.
# Tests that actually call LLM APIs will be skipped via the `needs_real_llm` marker.
_CI = os.getenv("CI") == "true"

if _CI and not os.getenv("BIGMODEL_API_KEY"):
    os.environ["BIGMODEL_API_KEY"] = "ci-dummy-key"

# Ensure OPENAI_API_KEY exists for legacy mode and tests that reference it
if _CI and not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "ci-dummy-openai-key"


import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "needs_real_llm: skip when no real LLM API key is available")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Skip tests marked needs_real_llm when running in CI."""
    marker = item.get_closest_marker("needs_real_llm")
    if marker and _CI:
        pytest.skip("skipped in CI (no real LLM API key)")
