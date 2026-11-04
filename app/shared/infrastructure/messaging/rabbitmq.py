from ..request_trace import request_id,valid
"""Native RabbitMQ request/reply, with no HTTP fallback between services."""
import base64
import json
import os
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4
import pika

SERVICES={'identity','properties','telemetry','analytics','reports','notifications','billing','config-service'}

class BrokerUnavailable(RuntimeError):
    pass

def connection():
    params=pika.URLParameters(os.environ['RABBITMQ_URL'])
    params.heartbeat=30
    params.socket_timeout=4
    params.blocked_connection_timeout=5
    return pika.BlockingConnection(params)

def rpc(service, path, token='', method='GET', body=None, internal=False, timeout=12):
    if service not in SERVICES or not path.startswith('/') or path.startswith('//'):
        raise ValueError('Invalid broker destination')
    headers={}
    if token: headers['Authorization']='Bearer '+token
    if internal: headers['X-Service-Token']=os.environ['INTERNAL_SERVICE_TOKEN']
    if body is not None: headers['Content-Type']='application/json'
    request={'traceId':request_id(),'method':method,'path':path,'headers':headers,
             'body':base64.b64encode(json.dumps(body).encode() if body is not None else b'').decode(),
             'deadline':int((time.time()+timeout)*1000)}
    conn=None
    try:
        conn=connection()
        channel=conn.channel()
        queue=channel.queue_declare(queue='',exclusive=True,auto_delete=True).method.queue
        correlation=str(uuid4())
        responses=[]
        def received(ch, method, properties, raw):
            if properties.correlation_id==correlation:
                if len(raw)>16*1024*1024: raise ValueError('Broker response too large')
                responses.append(json.loads(raw))
        channel.basic_consume(queue=queue,on_message_callback=received,auto_ack=True)
        channel.confirm_delivery()
        channel.basic_publish(exchange='hydrosmart.rpc',routing_key=service,mandatory=True,
            properties=pika.BasicProperties(reply_to=queue,correlation_id=correlation,
                                            content_type='application/json',delivery_mode=2,expiration='15000'),
            body=json.dumps(request).encode())
        deadline=time.monotonic()+timeout
        while not responses:
            if time.monotonic()>=deadline: raise TimeoutError()
            conn.process_data_events(time_limit=min(.25,max(0,deadline-time.monotonic())))
        result=responses[0]
        raw=base64.b64decode(result['body'],validate=True)
        return result['status'],raw,result.get('headers',{})
    except (pika.exceptions.AMQPError, OSError, TimeoutError, KeyError, ValueError) as exc:
        raise BrokerUnavailable('RabbitMQ request failed') from exc
    finally:
        if conn is not None and conn.is_open:
            conn.close()

def json_rpc(service,path,token='',method='GET',body=None,internal=False):
    status,raw,_=rpc(service,path,token,method,body,internal)
    return status,json.loads(raw) if raw else None

class RpcServer:
    def __init__(self,service):
        self.service=service
        self.stop_event=threading.Event()
        self.ready=threading.Event()
        self.connected=self.ready
        self.thread=threading.Thread(target=self.run,name=service+'-rpc',daemon=True)

    def start(self): self.thread.start()
    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)

    def handle(self,ch,method,props,raw):
        try:
            if len(raw)>16*1024*1024 or not props.reply_to or not props.correlation_id: raise ValueError()
            request=json.loads(raw)
            path=request['path']
            if not isinstance(path,str) or not path.startswith('/') or path.startswith('//') or '\r' in path or '\n' in path: raise ValueError()
            if int(request['deadline'])<int(time.time()*1000):
                status,data,headers=504,b'{"error":"expired_broker_request"}',{}
            else:
                headers={k:v for k,v in request.get('headers',{}).items() if k in ('Authorization','Content-Type','X-Service-Token','X-Request-ID')}
                headers['X-Request-ID']=valid(request.get('traceId'))
                local=Request('http://127.0.0.1:8080'+path,data=base64.b64decode(request.get('body',''),validate=True) or None,
                              headers=headers,method=request['method'])
                try:
                    with urlopen(local,timeout=20) as response:
                        status,data,headers=response.status,response.read(12*1024*1024),{'Content-Type':response.headers.get('Content-Type','application/json')}
                except HTTPError as response:
                    status,data,headers=response.code,response.read(12*1024*1024),{'Content-Type':'application/json'}
            result={'status':status,'headers':headers,'body':base64.b64encode(data).decode()}
        except (ValueError,KeyError,TypeError):
            ch.basic_reject(method.delivery_tag,requeue=False)
            return
        except Exception:
            result={'status':503,'headers':{'Content-Type':'application/json'},'body':base64.b64encode(b'{"error":"service_unavailable"}').decode()}
        ch.basic_publish(exchange='',routing_key=props.reply_to,body=json.dumps(result).encode(),
                         properties=pika.BasicProperties(correlation_id=props.correlation_id,content_type='application/json'))
        ch.basic_ack(method.delivery_tag)

    def run(self):
        while not self.stop_event.is_set():
            conn=None
            try:
                conn=connection()
                channel=conn.channel()
                channel.exchange_declare('hydrosmart.rpc','direct',durable=True)
                channel.queue_declare('rpc.'+self.service,durable=True)
                channel.queue_bind('rpc.'+self.service,'hydrosmart.rpc',self.service)
                channel.basic_qos(prefetch_count=8)
                channel.basic_consume('rpc.'+self.service,self.handle,auto_ack=False)
                self.ready.set()
                while not self.stop_event.is_set(): conn.process_data_events(time_limit=1)
            except Exception: pass
            finally:
                self.ready.clear()
                if conn is not None and conn.is_open:
                    try: conn.close()
                    except Exception: pass
            self.stop_event.wait(2)

