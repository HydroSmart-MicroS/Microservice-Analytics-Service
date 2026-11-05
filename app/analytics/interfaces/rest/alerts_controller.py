from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator
from fastapi import APIRouter,Depends,HTTPException
from ...infrastructure.authorization.sfs.configuration.jwt_authorization import authorized

class RulesResource(BaseModel):
    model_config=ConfigDict(extra='forbid')
    highEnabled:bool=True
    thresholdLiters:Decimal=Field(default=Decimal(100),gt=0,le=1000000,decimal_places=3)
    windowSeconds:int=Field(default=3600,ge=60,le=86400)
    leakEnabled:bool=True
    leakWindowSeconds:int=Field(default=180,ge=30,le=3600)
    normalStartHour:int=Field(default=6,ge=0,le=23)
    normalEndHour:int=Field(default=22,ge=0,le=23)
    leakAllDay:bool=False
    cooldownSeconds:int=Field(default=1800,ge=60,le=86400)
    @model_validator(mode='after')
    def hours(self):
        if self.leakEnabled and not self.leakAllDay and self.normalStartHour==self.normalEndHour:raise ValueError('El horario necesita dos horas distintas.')
        return self
class GoalResource(BaseModel):
    model_config=ConfigDict(extra='forbid')
    unitId:UUID
    budget:Decimal=Field(gt=0,le=1000000,decimal_places=2)
class DecisionResource(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:str=Field(pattern='^(confirmed|dismissed)$')

def router_for(service):
    router=APIRouter()
    @router.get('/api/v1/alerts/rules')
    def rules(unitId:UUID,actor=Depends(authorized)):return service.rules(str(unitId),actor[0])
    @router.put('/api/v1/alerts/rules/{unit}')
    def save_rules(unit:UUID,body:RulesResource,actor=Depends(authorized)):
        try:return service.save_rules(str(unit),actor[0],actor[1]['sub'],body.model_dump(mode='json'))
        except PermissionError as error:raise HTTPException(403,str(error))
    @router.get('/api/v1/alerts')
    def alerts(unitId:UUID,actor=Depends(authorized)):return service.alerts(str(unitId),actor[0],actor[1]['sub'])
    @router.post('/api/v1/alerts/{alert}/resolve')
    def resolve(alert:UUID,unitId:UUID,actor=Depends(authorized)):
        try:
            if not service.resolve(str(unitId),actor[0],actor[1]['sub'],str(alert)):raise HTTPException(404,'Alerta no encontrada.')
        except ValueError as error:raise HTTPException(409,str(error))
        return {'resolved':True}
    @router.post('/api/v1/alerts/{alert}/decision')
    def decision(alert:UUID,unitId:UUID,body:DecisionResource,actor=Depends(authorized)):
        try:
            if not service.resolve(str(unitId),actor[0],actor[1]['sub'],str(alert),body.decision):raise HTTPException(404,'Alerta no encontrada.')
        except ValueError as error:raise HTTPException(409,str(error))
        return {'status':body.decision}
    @router.get('/api/v1/goals')
    def current_goal(unitId:UUID,actor=Depends(authorized)):return service.current_goal(str(unitId),actor[0],actor[1]['sub'])
    @router.post('/api/v1/goals',status_code=201)
    def save_goal(body:GoalResource,actor=Depends(authorized)):
        try:return service.save_goal(str(body.unitId),actor[0],actor[1]['sub'],body.budget)
        except ValueError as error:raise HTTPException(400,str(error))
    return router

