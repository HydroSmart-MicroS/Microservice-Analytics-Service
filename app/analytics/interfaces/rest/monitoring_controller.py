from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from ...infrastructure.authorization.sfs.configuration.jwt_authorization import authorized
from .resources.tariff_resource import TariffResource
from .transform.tariff_transform import to_domain, to_resource

def router_for(queries, commands, dashboard):
    router = APIRouter()

    @router.get('/api/v1/tariffs')
    def current(unitId: UUID, category: str = Query(default='domestic', pattern='^(domestic|commercial)$'), reference: bool = False, actor=Depends(authorized)):
        token, _ = actor
        tariff = queries.current(str(unitId),token,category,reference)
        return to_resource(tariff)

    @router.get('/api/v1/tariffs/history')
    def history(unitId: UUID,actor=Depends(authorized)):
        return queries.history(str(unitId),actor[0])

    @router.put('/api/v1/tariffs/{unit_id}')
    def save(unit_id: UUID, resource: TariffResource, actor=Depends(authorized)):
        token, claims = actor
        try:
            return to_resource(commands.handle(str(unit_id),token,claims['sub'],to_domain(resource)))
        except ValueError as exc:
            raise HTTPException(400,str(exc))
        except PermissionError as exc:
            raise HTTPException(403,str(exc))

    @router.get('/api/v1/tariffs/estimate')
    def estimate(unitId: UUID, liters: Decimal = Query(ge=0,le=1000000000000), category: str = Query(default='domestic', pattern='^(domestic|commercial)$'), reference: bool = False, actor=Depends(authorized)):
        tariff,result = queries.estimate(str(unitId),actor[0],liters,category,reference)
        return {'estimate':result,'tariffName':tariff.name,'minimumBudget':str(tariff.minimum_budget()),
                'sourceUrl':tariff.source_url,'sourceDate':tariff.source_date}

    @router.get('/api/v1/analytics/dashboard')
    def summary(unitId: UUID, start: datetime | None = Query(default=None, alias='from'), end: datetime | None = Query(default=None, alias='to'), actor=Depends(authorized)):
        now = datetime.now(timezone.utc)
        start, end = start or (now-timedelta(days=31)), end or now
        if start.tzinfo is None or end.tzinfo is None or not start < end or end-start > timedelta(days=366):
            raise HTTPException(400,'Selecciona un período válido de hasta 366 días.')
        return dashboard.handle(str(unitId),actor[0],start,end)
    return router
