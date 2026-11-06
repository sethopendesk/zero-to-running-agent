"""Phase 1 graph: Gather -> Check -> Reason -> Decide -> Draft -> Review -> Save."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.act import draft_node, review_node, save_node, send_node
from agent.check import check_node
from agent.decide import after_decide, decide_node
from agent.gather import gather_node
from agent.reason import reason_node
from agent.state import AgentState


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("gather", gather_node)
    graph.add_node("check", check_node)
    graph.add_node("reason", reason_node)
    graph.add_node("decide", decide_node)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)
    # graph.add_node("save", save_node)
    graph.add_node("send", send_node)


    graph.add_edge(START, "gather")
    graph.add_edge("gather", "check")
    graph.add_edge("check", "reason")
    graph.add_edge("reason", "decide")
    graph.add_conditional_edges("decide", after_decide, {"draft": "draft", "end": END})
    graph.add_edge("draft", "review")
    graph.add_edge("review", "send")
    # graph.add_edge("save", END)
    graph.add_edge("send", END)
    return graph.compile(checkpointer=checkpointer if checkpointer is not None else MemorySaver())
