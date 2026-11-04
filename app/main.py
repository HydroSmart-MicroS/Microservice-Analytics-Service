from .shared.infrastructure.configuration import remote_configuration
from .shared.infrastructure.persistence.postgresql.connection_pool import close_pool,transaction
import os
from contextlib import asynccontextmanager
from .analytics.infrastructure.persistence.postgresql.repositories.pg_monitoring_repository import PgMonitoringRepository
from .analytics.interfaces.acl.monitoring_dependencies_facade import MonitoringDependenciesFacade
from .analytics.application.internal.commandservices.monitoring_command_service_impl import MonitoringCommandServiceImpl
from .analytics.application.internal.eventhandlers.monitoring_event_handler import MonitoringEventHandler
from .analytics.interfaces.messaging.monitoring_events_controller import MonitoringEventsController
from .analytics.infrastructure.messaging.rabbitmq.outbox_publisher import OutboxPublisher
from .analytics.infrastructure.persistence.postgresql.repositories.pg_tariff_repository import PgTariffRepository
from .shared.infrastructure.privacy import gate as lifecycle_gate
from .shared.infrastructure.messaging.rabbitmq import RpcServer
rpc_server=RpcServer("analytics")
from fastapi import FastAPI
from .analytics.infrastructure.persistence.postgresql.repositories.pg_consumption_repository import PgConsumptionRepository
from .analytics.application.internal.commandservices.consumption_command_service_impl import ConsumptionCommandServiceImpl
from .analytics.application.internal.eventhandlers.reading_recorded_event_handler import ReadingRecordedEventHandler
from .analytics.infrastructure.messaging.rabbitmq.reading_consumer import ReadingConsumer
from .analytics.interfaces.messaging.reading_events_controller import ReadingEventsController
from .analytics.application.internal.queryservices.health_query_service_impl import HealthQueryServiceImpl
from .analytics.infrastructure.messaging.rabbitmq.broker_health_probe import RabbitBrokerHealthProbe
from .analytics.interfaces.rest.health_controller import router_for

consumer = ReadingConsumer(os.environ["RABBITMQ_URL"], ReadingEventsController(ReadingRecordedEventHandler(ConsumptionCommandServiceImpl(PgConsumptionRepository()))).handle)

monitoring_repository=PgMonitoringRepository()
monitoring_dependencies=MonitoringDependenciesFacade()
monitoring_commands=MonitoringCommandServiceImpl(monitoring_repository,PgTariffRepository(),monitoring_dependencies)
monitoring_controller=MonitoringEventsController(MonitoringEventHandler(monitoring_repository,monitoring_dependencies,monitoring_commands))
def process_monitoring(body):
    import json
    from .analytics.infrastructure.persistence.postgresql.repositories.pg_erasure_repository import unit_erased
    from .shared.infrastructure.persistence.postgresql.connection_pool import connect
    with lifecycle_gate.read(),transaction(),connect() as conn:
        unit=json.loads(body).get('data',{}).get('unit_id','')
        if unit_erased(conn,unit):return False
        return monitoring_controller.handle(body)
monitoring_consumer=ReadingConsumer(os.environ["RABBITMQ_URL"],process_monitoring,queue="analytics.monitoring")
outbox=OutboxPublisher()

@asynccontextmanager
async def lifespan(app):
    consumer.start()
    monitoring_consumer.start()
    outbox.start()
    rpc_server.start()
    try:
        yield
    finally:
        consumer.stop()
        monitoring_consumer.stop()
        outbox.stop()
        rpc_server.stop()
        close_pool()

app = FastAPI(title="HydroSmart Analytics", version="0.2.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router_for(HealthQueryServiceImpl({'readingsConsumer':consumer,'monitoringConsumer':monitoring_consumer,'rpcReceiver':rpc_server},PgConsumptionRepository(),RabbitBrokerHealthProbe())))

from .analytics.infrastructure.persistence.postgresql.repositories.pg_tariff_repository import PgTariffRepository
from .analytics.interfaces.acl.monitoring_context_facade import MonitoringContextFacade
from .analytics.application.internal.commandservices.tariff_command_service_impl import TariffCommandServiceImpl
from .analytics.application.internal.queryservices.dashboard_query_service_impl import DashboardQueryServiceImpl
from .analytics.application.internal.queryservices.tariff_query_service_impl import TariffQueryServiceImpl
from .analytics.application.internal.queryservices.internal_estimate_query_service_impl import InternalEstimateQueryServiceImpl
from .analytics.interfaces.rest.monitoring_controller import router_for as monitoring_router
tariffs = PgTariffRepository()
monitoring = MonitoringContextFacade()
app.include_router(monitoring_router(TariffQueryServiceImpl(tariffs, monitoring), TariffCommandServiceImpl(tariffs, monitoring), DashboardQueryServiceImpl(tariffs, monitoring)))

from .analytics.interfaces.rest.alerts_controller import router_for as alerts_router
app.include_router(alerts_router(monitoring_commands))

from fastapi.responses import JSONResponse
from .shared.infrastructure.messaging.rabbitmq import BrokerUnavailable
@app.exception_handler(BrokerUnavailable)
async def unavailable_broker(request, error):
    return JSONResponse(status_code=503,content={"detail":"La comunicación por RabbitMQ no está disponible."})

from .analytics.interfaces.rest.internal_estimates_controller import router_for as estimates_router
app.include_router(estimates_router(InternalEstimateQueryServiceImpl(tariffs,monitoring_dependencies)))

from .analytics.interfaces.rest.account_erasure_controller import router_for as erasure_router
from .analytics.infrastructure.persistence.postgresql.repositories.pg_erasure_repository import PgAccountErasureRepository
app.include_router(erasure_router(PgAccountErasureRepository()))
import asyncio
@app.middleware('http')
async def lifecycle(request,call_next):
    authenticated=bool(request.headers.get('authorization'))
    if authenticated:await asyncio.to_thread(lifecycle_gate.acquire)
    try:return await call_next(request)
    finally:
        if authenticated:lifecycle_gate.release()

from .shared.infrastructure.request_trace import middleware as trace_middleware
app.middleware("http")(trace_middleware)
