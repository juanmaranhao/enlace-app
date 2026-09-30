"""Cliente portátil sem Django. A falha da central não é sucesso da tarefa."""
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse

class EnlaceUnavailable(Exception):pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class EnlaceClient:
    def __init__(self,url,token,timeout=5):
        parsed=urlparse(url)
        if parsed.scheme not in {'http','https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('URL da central inválida.')
        if parsed.scheme=='http' and parsed.hostname not in {'localhost','127.0.0.1','::1'}:raise ValueError('HTTP sem TLS é permitido apenas no loopback.')
        self.url=url.rstrip('/')+'/api/conector/';self.token=token;self.timeout=timeout
    def call(self,action,**arguments):
        request=urllib.request.Request(self.url,data=json.dumps({'action':action,**arguments}).encode(),method='POST',headers={'Content-Type':'application/json','Authorization':f'Bearer {self.token}'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=self.timeout) as response:
                raw=response.read(1024*1024+1)
                if len(raw)>1024*1024:raise ValueError()
                return json.loads(raw)
        except (OSError,ValueError) as exc:raise EnlaceUnavailable('Central indisponível, credencial recusada ou resposta incompatível. Nenhuma consulta deve ser simulada.') from exc

class EventBuffer:
    """Fila em memória: emit não usa rede. O host decide quando/onde drenar."""
    def __init__(self,client,capacity=500):
        from threading import Lock
        self.client=client;self.capacity=capacity;self.events=[];self.dropped=0;self.lock=Lock();self.flush_lock=Lock()
    def emit(self,event):
        from copy import deepcopy
        with self.lock:
            if len(self.events)>=self.capacity:self.dropped+=1;return False
            self.events.append(deepcopy(event));return True
    def flush(self):
        if not self.flush_lock.acquire(blocking=False):return False
        try:return self._flush()
        finally:self.flush_lock.release()
    def _flush(self):
        with self.lock:batch=list(self.events[:100])
        if not batch:return True
        try:result=self.client.call('events',events=batch)
        except EnlaceUnavailable:return False
        if result.get('accepted')!=len(batch):return False
        with self.lock:del self.events[:len(batch)]
        return True
