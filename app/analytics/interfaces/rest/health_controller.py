from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ...domain.services.health_query_service import HealthQueryService
from .transform.health_resource_from_entity_assembler import to_resource

def router_for(queries: HealthQueryService):
    router = APIRouter()

    @router.get("/health/live")
    def live():
        return to_resource(True)

    @router.get("/health/ready")
    def ready():
        components=queries.components()
        healthy=all(component['status']=='UP' for component in components.values())
        return JSONResponse(status_code=200 if healthy else 503,content=to_resource(healthy,components),headers={'Cache-Control':'no-store'})

    return router
