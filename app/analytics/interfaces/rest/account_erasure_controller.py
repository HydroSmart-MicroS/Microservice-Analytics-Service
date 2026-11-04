import os,hmac
from uuid import UUID
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
from ...domain.services.account_erasure import AccountErasure
class Erasure(BaseModel):unitIds:list[UUID]=Field(max_length=10000)
def router_for(service:AccountErasure):
    router=APIRouter()
    @router.post('/internal/v1/privacy/{user}/erase')
    def remove(user:str,body:Erasure,service_token:str=Header(default='',alias='X-Service-Token')):
        expected=os.environ.get('INTERNAL_SERVICE_TOKEN','')
        if len(expected)<32 or not hmac.compare_digest(expected,service_token):raise HTTPException(401)
        service.erase(user,[str(unit) for unit in body.unitIds])
        return {'erased':True}
    return router
