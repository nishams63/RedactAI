import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.agent_registry import AgentRegistryModel, AgentMetricsLog

logger = logging.getLogger("redactai.agents.registry")

class AgentRegistry:
    def __init__(self, db: Session):
        self.db = db

    def register_agent(self, spec: Dict[str, Any]) -> AgentRegistryModel:
        """Self-registers an agent with its capabilities, version, input/output schemas, and policies."""
        agent_id = spec["agent_id"]
        version = spec["version"]
        
        record = self.db.query(AgentRegistryModel).filter(
            AgentRegistryModel.agent_id == agent_id,
            AgentRegistryModel.version == version
        ).first()

        if not record:
            record = AgentRegistryModel(
                agent_id=agent_id,
                version=version,
                name=spec["name"],
                description=spec.get("description"),
                is_active=spec.get("is_active", True),
                capabilities=spec.get("capabilities", []),
                supported_tasks=spec.get("supported_tasks", []),
                input_schema=spec.get("input_schema", {}),
                output_schema=spec.get("output_schema", {}),
                policy=spec.get("policy", {}),
                health_status="HEALTHY"
            )
            self.db.add(record)
        else:
            record.name = spec["name"]
            record.description = spec.get("description")
            record.is_active = spec.get("is_active", True)
            record.capabilities = spec.get("capabilities", [])
            record.supported_tasks = spec.get("supported_tasks", [])
            record.input_schema = spec.get("input_schema", {})
            record.output_schema = spec.get("output_schema", {})
            record.policy = spec.get("policy", {})

        self.db.commit()
        self.db.refresh(record)

        metric = self.db.query(AgentMetricsLog).filter(
            AgentMetricsLog.agent_id == agent_id,
            AgentMetricsLog.version == version
        ).first()
        if not metric:
            metric = AgentMetricsLog(agent_id=agent_id, version=version)
            self.db.add(metric)
            self.db.commit()

        return record

    def get_agent(self, agent_id: str, version: Optional[str] = None) -> Optional[AgentRegistryModel]:
        """Fetches active agent. If version is omitted, returns the latest registered version."""
        query = self.db.query(AgentRegistryModel).filter(
            AgentRegistryModel.agent_id == agent_id,
            AgentRegistryModel.is_active == True
        )
        if version:
            return query.filter(AgentRegistryModel.version == version).first()
        else:
            return query.order_by(AgentRegistryModel.version.desc()).first()

    def discover_by_capability(self, required_capabilities: List[str]) -> List[AgentRegistryModel]:
        """Discovers active agents that support all required capabilities."""
        all_active = self.db.query(AgentRegistryModel).filter(
            AgentRegistryModel.is_active == True
        ).all()

        matched = []
        for agent in all_active:
            if all(cap in agent.capabilities for cap in required_capabilities):
                matched.append(agent)
                
        matched.sort(key=lambda x: x.version, reverse=True)
        return matched

    def toggle_agent_active(self, agent_id: str, version: str, is_active: bool) -> Optional[AgentRegistryModel]:
        """Enables deployment activation or deactivation rollbacks."""
        record = self.db.query(AgentRegistryModel).filter(
            AgentRegistryModel.agent_id == agent_id,
            AgentRegistryModel.version == version
        ).first()
        if record:
            record.is_active = is_active
            self.db.commit()
            self.db.refresh(record)
        return record
