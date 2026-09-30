"""Recuperação local com fontes: não inventa capacidades nem chama provedores."""
import re
import unicodedata

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))

STOP = {'como','faco','fazer','criar','quero','para','uma','um','por','que','qual','fluxo','projeto','me','ajude','de','e','o','a','os','as','do','da','no','na'}
EXPANSIONS = {'sites':['site','frontend','landing','website'], 'site':['site','frontend','landing','website'],
              'videos':['video','comfyui'], 'video':['video','comfyui'], 'documentos':['documento','etp'],
              'publicacoes':['publicacao','social','post']}

def search(graph, query, limit=8):
    terms = [t for t in re.findall(r'[a-z0-9_-]+',normalize(query)) if t not in STOP and len(t)>2]
    if not terms: return []
    groups = [EXPANSIONS.get(t,[t]) for t in terms]
    sources = {s['id']:s for s in graph.get('sources',[])}
    results = []
    for node in graph.get('nodes',[]):
        source = sources.get(node['source_id'],{})
        title = normalize(node['name']+' '+node['summary'])
        text=source.get('text','')
        if node['kind']=='flow':text='\n'.join(text.splitlines()[node['line']-1:node.get('end_line',len(text.splitlines()))])
        body = normalize(text)
        matched = [term for group in groups for term in group if term in title or term in body]
        if not matched: continue
        score = sum(5 if any(t in title for t in group) else 1 if any(t in body for t in group) else 0 for group in groups)
        score += 1 if node['kind']=='flow' else 0
        excerpts=[line.strip() for line in text.splitlines() if any(term in normalize(line) for term in matched)]
        excerpt=' '.join(excerpts[:2])[:350] if excerpts else node['summary']
        results.append({**node,'score':score,'matched':sorted(set(matched)),'excerpt':excerpt})
    return sorted(results,key=lambda n:(-n['score'],n['name']))[:limit]
