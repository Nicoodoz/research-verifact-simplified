"""Same Alibaba POST, add sanitized error types only; no retry/provider/body changes."""
import json,urllib.request,urllib.error
from verifact_research.inference.aliyun import AliyunClient,NoRedirect
import core024 as c
class DiagnosticClient(AliyunClient):
    def send(self,body):
        self.validate(body);started=c.now();diagnostic={}
        req=urllib.request.Request(self.config.endpoint,data=c.canonical(body).encode('utf-8'),method='POST',headers={'Authorization':'Bearer '+self.config.api_key,'Content-Type':'application/json'})
        try:
            try:
                with urllib.request.build_opener(NoRedirect()).open(req,timeout=self.timeout) as r:status,raw,headers=r.status,r.read(),r.headers
            except urllib.error.HTTPError as exc:status,raw,headers=exc.code,exc.read(),exc.headers or {}
        except (OSError,urllib.error.URLError) as exc:
            status,raw,headers=0,b'',{}
            reason=getattr(exc,'reason',None)
            diagnostic=dict(exception_type=type(exc).__name__,reason_type=type(reason).__name__,errno=getattr(exc,'errno',None),reason_errno=getattr(reason,'errno',None))
        tr=dict(http_status=status,body_text=raw.decode('utf-8',errors='replace'),headers={k.lower():v for k,v in headers.items() if k.lower() in {'x-request-id','x-dashscope-request-id','retry-after'}},outcome_unknown=status==0,started_utc=started,ended_utc=c.now(),transport_diagnostic=diagnostic)
        def redact(v):
            if isinstance(v,str):return v.replace(self.config.api_key,'[REDACTED_API_KEY]').replace(json.dumps(self.config.api_key)[1:-1],'[REDACTED_API_KEY]')
            if isinstance(v,dict):return {k:redact(x) for k,x in v.items()}
            return v
        return redact(tr)
