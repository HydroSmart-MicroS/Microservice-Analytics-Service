import json
import os
from ..messaging.rabbitmq import json_rpc

def load_config():
    base = os.environ.get("CONFIG_SERVICE_URL")
    if not base:
        return
    status,values=json_rpc('config-service','/v1/config/analytics/local')
    if status!=200: raise RuntimeError('Configuration broker unavailable')
    if not isinstance(values, dict) or set(values) != {"DATABASE_CONNECT_TIMEOUT"}:
        raise RuntimeError("Invalid remote configuration")
    timeout = values["DATABASE_CONNECT_TIMEOUT"]
    if not isinstance(timeout, str) or not timeout.isdigit() or not 1 <= int(timeout) <= 30:
        raise RuntimeError("Invalid connection timeout")
    for key, value in values.items():
        os.environ.setdefault(key, value)
    print("Loaded analytics configuration from Config Service")

load_config()
