from dataclasses import dataclass

from langgraph.pregel import Pregel

from agents.logmind import logmind
from schema import AgentInfo

DEFAULT_AGENT = "logmind"
AgentGraph = Pregel


@dataclass
class Agent:
    description: str
    graph: AgentGraph


agents: dict[str, Agent] = {
    "logmind": Agent(
        description="智能日志分析与运维排障 Agent，支持异常堆栈解析、故障原因分析和修复建议生成。",
        graph=logmind,
    )
}


async def load_agent(agent_id: str) -> None:
    """Validate the requested LogMind graph during service startup."""
    if agent_id not in agents:
        raise KeyError(agent_id)


def get_agent(agent_id: str) -> AgentGraph:
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    return [AgentInfo(key=agent_id, description=agent.description) for agent_id, agent in agents.items()]
