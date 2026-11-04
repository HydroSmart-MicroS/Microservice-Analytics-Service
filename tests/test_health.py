import unittest,threading
from types import SimpleNamespace
from app.analytics.application.internal.queryservices.health_query_service_impl import HealthQueryServiceImpl
from app.analytics.interfaces.rest.health_controller import router_for
class HealthTests(unittest.TestCase):
    def test_independent_diagnostics_and_sanitized_failures(self):
        class Database:
            def ready(self):raise RuntimeError('postgresql://private:password@host')
        class Broker:
            def diagnostics(self):return {'ready':True,'connection':'UP'}
        connected=threading.Event();connected.set()
        service=HealthQueryServiceImpl({'rpcReceiver':SimpleNamespace(connected=connected)},Database(),Broker())
        result=service.components()
        self.assertEqual(result['database']['status'],'DOWN');self.assertEqual(result['rabbitmq']['status'],'UP')
        self.assertNotIn('postgresql://',str(result))
        routes=router_for(service).routes
        self.assertEqual(next(r.endpoint for r in routes if r.path=='/health/ready')().status_code,503)
        self.assertEqual(next(r.endpoint for r in routes if r.path=='/health/live')()['status'],'UP')
        connected.clear();self.assertEqual(service.components()['rabbitmq']['status'],'DOWN')
    def test_missing_broker_does_not_hide_database_health(self):
        class Database:
            def ready(self):return True
        class Broker:
            def diagnostics(self):raise RuntimeError('amqp://private:secret@host')
        result=HealthQueryServiceImpl({},Database(),Broker()).components()
        self.assertEqual(result['database']['status'],'UP');self.assertEqual(result['rabbitmq']['status'],'DOWN');self.assertNotIn('secret',str(result))
