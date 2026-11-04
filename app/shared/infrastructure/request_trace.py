import re,time,json,logging
from uuid import uuid4
from contextvars import ContextVar
current=ContextVar('request_id',default=None)
def request_id():return current.get() or str(uuid4())
def valid(value):return value if value and re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value) else str(uuid4())
async def middleware(request,call_next):
    identity=valid(request.headers.get('x-request-id'));token=current.set(identity);started=time.perf_counter();status=500
    try:
        response=await call_next(request);status=response.status_code;response.headers['X-Request-ID']=identity;return response
    finally:
        logging.getLogger('uvicorn.error').info(json.dumps({'event':'http_request','service':'analytics','requestId':identity,'method':request.method,'path':re.sub(r'/[A-Za-z0-9_-]{20,}','/:id',request.url.path),'status':status,'durationMs':round((time.perf_counter()-started)*1000,2)}))
        current.reset(token)
