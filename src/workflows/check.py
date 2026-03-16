"""Info check workflow using LangGraph."""

from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from ..agents.message_parser import MessageParserAgent
from ..agents.search_query import SearchQueryAgent
from ..agents.verifier import VerifierAgent
from ..agents.synthesizer import SynthesizerAgent
from ..search.aggregator import get_aggregator


class CheckState(TypedDict):
    """State for info check workflow."""
    original_message: str
    parsed: Optional[dict]
    queries: Optional[List[dict]]
    search_results: Optional[List[dict]]
    verification: Optional[dict]
    report: Optional[str]


class InfoCheckWorkflow:
    """LangGraph-based info checking workflow with multi-channel search."""
    
    def __init__(self):
        self.parser = MessageParserAgent()
        self.query_generator = SearchQueryAgent()
        self.verifier = VerifierAgent()
        self.synthesizer = SynthesizerAgent()
        self.search_aggregator = get_aggregator()
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(CheckState)
        
        # Add nodes
        workflow.add_node("parse", self._parse_node)
        workflow.add_node("generate_queries", self._generate_queries_node)
        workflow.add_node("search", self._search_node)
        workflow.add_node("verify", self._verify_node)
        workflow.add_node("synthesize", self._synthesize_node)
        
        # Add edges
        workflow.set_entry_point("parse")
        workflow.add_edge("parse", "generate_queries")
        workflow.add_edge("generate_queries", "search")
        workflow.add_edge("search", "verify")
        workflow.add_edge("verify", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _parse_node(self, state: CheckState) -> CheckState:
        """Parse the message."""
        message = state["original_message"]
        parsed = self.parser.parse(message)
        return {"parsed": parsed}
    
    def _generate_queries_node(self, state: CheckState) -> CheckState:
        """Generate search queries."""
        parsed = state["parsed"]
        queries = self.query_generator.generate_queries(parsed)
        return {"queries": queries}
    
    def _search_node(self, state: CheckState) -> CheckState:
        """Execute multi-channel search."""
        queries = state.get("queries", [])
        
        # Extract query strings
        query_strings = [q.get("query", "") for q in queries[:3]]
        
        # Use aggregator to search across all sources
        all_results = self.search_aggregator.search_parallel(
            query_strings,
            max_per_source=2
        )
        
        return {"search_results": all_results}
    
    def _verify_node(self, state: CheckState) -> CheckState:
        """Verify the message."""
        message = state["original_message"]
        results = state.get("search_results", [])
        verification = self.verifier.verify(message, results)
        return {"verification": verification}
    
    def _synthesize_node(self, state: CheckState) -> CheckState:
        """Generate final report."""
        report = self.synthesizer.synthesize(
            state["original_message"],
            state.get("parsed", {}),
            state.get("queries", []),
            state.get("verification", {}),
            state.get("search_results", [])
        )
        return {"report": report}
    
    def run(self, message: str) -> str:
        """Run the full workflow."""
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
    """Factory function to create workflow."""
    return InfoCheckWorkflow()
