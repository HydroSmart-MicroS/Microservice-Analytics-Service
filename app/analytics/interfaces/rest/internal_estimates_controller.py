import os
import hmac
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter,Header,HTTPException,Query

def router_for(queries):
    router=APIRouter()
    @router.get('/internal/v1/analytics/estimate')
    def quote(unitId:UUID,start:datetime=Query(alias='from'),end:datetime=Query(alias='to'),service_token:str=Header(default='',alias='X-Service-Token')):
        expected=os.environ.get('INTERNAL_SERVICE_TOKEN','')
        if len(expected)<32 or not hmac.compare_digest(service_token,expected):raise HTTPException(401,'Servicio no autorizado.')
        try:return queries.handle(str(unitId),start,end)
        except ValueError as error:raise HTTPException(400,str(error))
        except LookupError as error:raise HTTPException(404,str(error))
    return router

