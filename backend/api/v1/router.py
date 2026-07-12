"""API v1 router — aggregates all endpoint modules."""
from fastapi import APIRouter
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.organizations import router as organizations_router
from api.v1.documents import router as documents_router
from api.v1.ml import router as ml_router
try:
    from api.v1.dl import router as dl_router
except ImportError:
    dl_router = None
from api.v1.legal import router as legal_router
from api.v1.security import router as security_router
from api.v1.release import router as release_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(ml_router)
if dl_router is not None:
    api_v1_router.include_router(dl_router)
api_v1_router.include_router(legal_router)
api_v1_router.include_router(security_router)
api_v1_router.include_router(release_router)
