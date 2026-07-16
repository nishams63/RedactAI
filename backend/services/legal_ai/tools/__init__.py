from services.legal_ai.tools.base import BaseTool
from services.legal_ai.tools.clause_explainer import ClauseExplainerTool
from services.legal_ai.tools.risk_analyzer import RiskAnalyzerTool
from services.legal_ai.tools.summarizer import ContractSummarizerTool
from services.legal_ai.tools.timeline import TimelineExtractorTool
from services.legal_ai.tools.entity_search import EntitySearchTool
from services.legal_ai.tools.compliance_checker import ComplianceCheckerTool
from services.legal_ai.tools.citation_validator import CitationValidatorTool

ALL_TOOLS = {
    "clause_explainer": ClauseExplainerTool(),
    "risk_analyzer": RiskAnalyzerTool(),
    "contract_summarizer": ContractSummarizerTool(),
    "timeline_extractor": TimelineExtractorTool(),
    "entity_search": EntitySearchTool(),
    "compliance_checker": ComplianceCheckerTool(),
    "citation_validator": CitationValidatorTool()
}
