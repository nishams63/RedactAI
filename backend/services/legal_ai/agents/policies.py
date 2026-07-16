import time
import logging
from typing import Dict, Any, List
from fastapi import HTTPException

logger = logging.getLogger("redactai.agents.policies")

class PolicyEngine:
    @staticmethod
    def validate_execution_policy(
        policy: Dict[str, Any],
        org_id: str,
        requested_tool: str | None = None,
        requested_model: str | None = None
    ) -> bool:
        """Validates if execution context complies with configured policies."""
        # 1. Tenancy Isolation policy
        allowed_orgs = policy.get("allowed_organizations", [])
        if allowed_orgs and str(org_id) not in [str(o) for o in allowed_orgs]:
            logger.warning(f"Tenant isolation breach: Org {org_id} not allowed by policy.")
            raise HTTPException(status_code=403, detail="Organization context not authorized by agent policy.")

        # 2. Tool authorization policy
        if requested_tool:
            allowed_tools = policy.get("allowed_tools", [])
            if allowed_tools and "*" not in allowed_tools and requested_tool not in allowed_tools:
                logger.warning(f"Policy violation: Tool {requested_tool} not allowed.")
                raise HTTPException(status_code=403, detail=f"Tool '{requested_tool}' is not authorized for this agent.")

        # 3. Model authorization policy
        if requested_model:
            allowed_models = policy.get("allowed_models", [])
            if allowed_models and "*" not in allowed_models and requested_model not in allowed_models:
                logger.warning(f"Policy violation: Model {requested_model} not allowed.")
                raise HTTPException(status_code=403, detail=f"LLM model '{requested_model}' is not authorized for this agent.")

        return True
