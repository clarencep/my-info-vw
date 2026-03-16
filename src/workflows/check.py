"""Info check workflow using LangGraph.

This module implements a LangGraph-based workflow for fact-checking messages
with multi-channel search capabilities. The workflow follows a linear path with
conditional branching for handling edge cases like empty search results.

Workflow Flow:
    Parse → SearchQuery → Search → [Verify | Skip] → Synthesize

The workflow can gracefully handle cases where search returns no results by
skipping the verification step and proceeding directly to synthesis with an
appropriate message.
"""

from typing import TypedDict, List, Optional, Dict, Any, Literal
import logging
from langgraph.graph import StateGraph, END

from ..agents.message_parser import MessageParserAgent
from ..agents.search_query import SearchQueryAgent
from ..agents.verifier import VerifierAgent
from ..agents.synthesizer import SynthesizerAgent
from ..search.aggregator import get_aggregator

logger = logging.getLogger(__name__)


class CheckState(TypedDict):
    """State for info check workflow.

    Attributes:
        original_message: The input message to be fact-checked.
        parsed: Parsed message structure from the parser agent.
        queries: Generated search queries for finding evidence.
        search_results: Aggregated search results from multiple sources.
        verification: Verification result with truth assessment.
        report: Final synthesized report.
    """
    original_message: str
    parsed: Optional[Dict[str, Any]]
    queries: Optional[List[Dict[str, Any]]]
    search_results: Optional[List[Dict[str, Any]]]
    verification: Optional[Dict[str, Any]]
    report: Optional[str]


class InfoCheckWorkflow:
    """LangGraph-based info checking workflow with multi-channel search.

    This workflow orchestrates the fact-checking process through multiple stages:
    1. Parse: Extract structured information from the message
    2. Generate Queries: Create search queries based on parsed content
    3. Search: Execute multi-channel search across configured providers
    4. Verify: Analyze search results to assess message accuracy
    5. Synthesize: Generate a comprehensive report with findings

    The workflow includes conditional logic to handle edge cases gracefully,
    such as when search returns no results.
    """

    def __init__(self) -> None:
        """Initialize the workflow with all required agents and components."""
        self.parser = MessageParserAgent()
        self.query_generator = SearchQueryAgent()
        self.verifier = VerifierAgent()
        self.synthesizer = SynthesizerAgent()
        self.search_aggregator = get_aggregator()

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with nodes and edges.

        Returns:
            A compiled StateGraph ready for execution.
        """
        workflow = StateGraph(CheckState)

        # Add nodes - each node represents a processing step
        workflow.add_node("parse", self._parse_node)
        workflow.add_node("generate_queries", self._generate_queries_node)
        workflow.add_node("search", self._search_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)

        # Add edges - define the workflow flow
        workflow.set_entry_point("parse")
        workflow.add_edge("parse", "generate_queries")
        workflow.add_edge("generate_queries", "search")

        # Conditional edge: check if search returned results
        workflow.add_conditional_edges(
            "search",
            self._should_verify,
            {
                "verify": "verify",
                "skip_verify": "synthesize"
            }
        )

        workflow.add_edge("verify", "synthesize")
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    def _parse_node(self, state: CheckState) -> Dict[str, Any]:
        """Parse the original message to extract structured information.

        Args:
            state: Current workflow state containing the original message.

        Returns:
            Dictionary with the 'parsed' key containing structured message data.
        """
        message = state["original_message"]
        parsed = self.parser.parse(message)
        return {"parsed": parsed}

    def _generate_queries_node(self, state: CheckState) -> Dict[str, Any]:
        """Generate search queries based on parsed message content.

        Args:
            state: Current workflow state with parsed message structure.

        Returns:
            Dictionary with the 'queries' key containing search query objects.
        """
        parsed = state["parsed"]
        queries = self.query_generator.generate_queries(parsed)
        return {"queries": queries}

    def _search_node(self, state: CheckState) -> Dict[str, Any]:
        """Execute multi-channel search across all configured providers.

        This node searches using the generated queries and aggregates results
        from multiple search sources configured in the search aggregator.

        Args:
            state: Current workflow state with search queries.

        Returns:
            Dictionary with the 'search_results' key containing aggregated results.
        """
        queries = state.get("queries", [])

        # Extract query strings from query objects
        query_strings = [q.get("query", "") for q in queries[:3]]

        # Use aggregator to search across all configured sources
        all_results = self.search_aggregator.search_parallel(
            query_strings,
            max_per_source=2
        )

        logger.info(f"Search returned {len(all_results)} results")
        return {"search_results": all_results}

    def _verify_node(self, state: CheckState) -> Dict[str, Any]:
        """Verify the original message against search results.

        This node analyzes the search results to assess the accuracy and
        truthfulness of the original message.

        Args:
            state: Current workflow state with message and search results.

        Returns:
            Dictionary with the 'verification' key containing assessment data.
        """
        message = state["original_message"]
        results = state.get("search_results", [])
        verification = self.verifier.verify(message, results)
        return {"verification": verification}

    def _synthesize_node(self, state: CheckState) -> Dict[str, Any]:
        """Generate the final report based on all workflow outputs.

        This node creates a comprehensive report that includes the analysis
        findings, verification results, and conclusions. If no search results
        were found, it will include a note about lack of evidence.

        Args:
            state: Current workflow state with all accumulated data.

        Returns:
            Dictionary with the 'report' key containing the final report text.
        """
        report = self.synthesizer.synthesize(
            state["original_message"],
            state.get("parsed", {}),
            state.get("queries", []),
            state.get("verification", {}),
            state.get("search_results", [])
        )
        return {"report": report}

    def _should_verify(self, state: CheckState) -> Literal["verify", "skip_verify"]:
        """Determine if verification should proceed based on search results.

        This conditional edge function checks if search returned any results.
        If no results were found, it skips verification to avoid processing
        empty data and proceeds directly to synthesis.

        Args:
            state: Current workflow state with search results.

        Returns:
            "verify" if search results exist, "skip_verify" otherwise.
        """
        search_results = state.get("search_results", [])

        if not search_results or len(search_results) == 0:
            logger.warning(
                "Search returned no results. Skipping verification and "
                "proceeding directly to synthesis with no-evidence message."
            )
            return "skip_verify"

        return "verify"

    def run(self, message: str) -> str:
        """Run the full workflow on a message.

        This is the main entry point for executing the fact-checking workflow.
        It initializes the workflow state and executes all nodes in sequence,
        handling any conditional branching along the way.

        Args:
            message: The message to be fact-checked.

        Returns:
            The final report text, or a fallback message if report generation fails.
        """
        initial_state: CheckState = {
            "original_message": message,
            "parsed": None,
            "queries": None,
            "search_results": None,
            "verification": None,
            "report": None
        }

        result = self.graph.invoke(initial_state)
        return result.get("report", "No report generated")


def create_workflow() -> InfoCheckWorkflow:
    """Factory function to create a new InfoCheckWorkflow instance.

    Returns:
        A new InfoCheckWorkflow instance ready for use.
    """
    return InfoCheckWorkflow()
