from fastapi import APIRouter
from core.optional_dependencies import OptionalDependencyManager

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/dependencies")
def get_system_dependencies():
    """Returns JSON manifest of optional AI dependencies and their installation status."""
    return OptionalDependencyManager.get_all_status()
