"""Inventário determinístico de instruções. Presença e referência não provam execução."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import os
import re
import json

from .paths import EXCLUDED, catalog_path, read_source

SCHEMA_VERSION = 2
MAX_FILES = 1800
MAX_TOTAL_BYTES = 8 * 1024 * 1024

def stable_id(kind, value):
    return sha256(f'{kind}:{value}'.encode()).hexdigest()[:24]

def redact(text):
    text = re.sub(r'(?im)^([^\n]*?(?:api[_-]?key|jev_ia|enlace_token|authorization|password|senha|secret[_-]?key|access[_-]?token)\s*[:=]\s*)(.+)$', r'\1[valor oculto]', text)
    return re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})', '[credencial oculta]', text)

def candidates(root):
    root = Path(root).resolve()
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        relative = parent.relative_to(root)
        dirs[:] = [name for name in sorted(dirs) if name.lower() not in EXCLUDED
                   and not (parent / name).is_symlink() and not (parent / name).is_junction()
                   and ((not relative.parts and name.lower() in {'docs', '.agents', '.codex'})
                        or (relative.parts and relative.parts[0].lower() == '.agents' and (len(relative.parts) > 1 or name.lower() == 'skills'))
                        or (relative.parts and relative.parts[0].lower() == '.codex' and len(relative.parts) == 1 and name.lower() == 'agents')
                        or (relative.parts and relative.parts[0].lower() == 'docs' and (len(relative.parts) > 1 or name.lower() in {'agentica','arquitetura','fluxos','contratos'})))]
        for filename in sorted(files):
            path = (relative / filename).as_posix()
            if catalog_path(path):
                yield path

def kind_for(path):
    lower = path.lower()
    if lower.endswith('/skill.md'): return 'skill'
    if lower.startswith('.codex/agents/'): return 'agent'
    if Path(lower).name == 'agents.md': return 'rule'
    if any(term in lower for term in ['contrato', 'identidade', 'design_aprovado']): return 'contract'
    return 'guide'

def summarize(text):
    description = re.search(r'(?m)^description:\s*["\']?(.+)', text)
    if description:
        return description.group(1).strip('"\' ')[:240]
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith(('#', '---', '```', '|', 'name:'))]
    return re.sub(r'[*`_]', '', ' '.join(lines[:2]))[:240]

def collect(root, progress=lambda count: None, cancelled=lambda: False):
    sources, nodes, warnings = [], [], []
    total_bytes = 0
    for index, path in enumerate(candidates(root)):
        if cancelled(): raise InterruptedError('Coleta cancelada.')
        if index >= MAX_FILES:
            warnings.append('Limite de fontes alcançado; cobertura parcial.')
            break
        try:
            text = redact(read_source(root, path))
        except (OSError, ValueError, UnicodeError):
            warnings.append({'path':path,'reason':'Fonte não lida: acesso, formato, origem ou tamanho incompatível.'})
            continue
        total_bytes += len(text.encode())
        if total_bytes > MAX_TOTAL_BYTES:
            warnings.append('Limite total de conteúdo alcançado; cobertura parcial.')
            break
        digest = sha256(text.encode()).hexdigest()
        heading = re.search(r'(?m)^#\s+(.+)', text)
        name = heading.group(1).strip() if heading else Path(path).stem
        if kind_for(path) == 'skill': name = PurePosixPath(path).parent.name
        ident = stable_id('source', path)
        sources.append({'id':ident,'path':path,'digest':digest,'text':text})
        nodes.append({'id':ident,'name':name[:120],'kind':kind_for(path),'path':path,'summary':summarize(text),
                      'evidence':'declared','source_id':ident,'line':1,'support':True})
        progress(len(sources))
    skills = {PurePosixPath(n['path']).parent.name:n for n in nodes if n['kind']=='skill'}
    relationships = []
    for source in sources:
        for name, skill in skills.items():
            if skill['id'] != source['id'] and re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', source['text']):
                relationships.append({'source':source['id'],'target':skill['id'],'kind':'reference','label':'Referencia'})
        is_flow_document=PurePosixPath(source['path']).name.lower() in {'fluxos.md','workflows.md'}
        is_skill=source['path'].lower().endswith('/skill.md')
        if is_flow_document or is_skill:
            sections = list(re.finditer(r'(?m)^#{2,3}\s+(.+)', source['text']))
            repeated_titles={}
            for i, section in enumerate(sections):
                if not is_flow_document and not re.search(r'(?i)fluxo|cria[çc][aã]o|ingest[aã]o|revis[aã]o',section.group(1)):continue
                chunk = source['text'][section.end():sections[i+1].start() if i+1<len(sections) else len(source['text'])]
                mentioned = [n for name,n in skills.items() if re.search(r'(?<![\w-])'+re.escape(name)+r'(?![\w-])',chunk)]
                if is_skill:mentioned.append(next(n for n in nodes if n['id']==source['id']))
                if not mentioned: continue
                title = section.group(1).strip()
                occurrence=repeated_titles.get(title,0);repeated_titles[title]=occurrence+1
                identity_title=title if not occurrence else f'{title}:occurrence:{occurrence}'
                ident = stable_id('flow',source['path']+':'+identity_title)
                nodes.append({'id':ident,'name':title[:120],'kind':'flow','path':source['path'],'summary':summarize(chunk),
                              'evidence':'declared','source_id':source['id'],'line':source['text'][:section.start()].count('\n')+1,
                              'end_line':source['text'][:sections[i+1].start()].count('\n') if i+1<len(sections) else len(source['text'].splitlines()),'support':False})
                relationships.extend({'source':ident,'target':n['id'],'kind':'reference','label':'Cita esta skill'} for n in mentioned)
                relationships.append({'source':ident,'target':source['id'],'kind':'support','label':'Fonte do fluxo'})
    by_path = {s['path']:s for s in sources}
    for source in sources:
        for reference in re.findall(r'\[[^\]]+\]\(([^)]+)\)', source['text']):
            reference = reference.split('#')[0].replace('\\','/')
            if not reference or '://' in reference: continue
            paths = [str(PurePosixPath(source['path']).parent / reference), reference]
            for path in paths:
                normalized = os.path.normpath(path).replace('\\','/')
                other = by_path.get(normalized)
                if other and other['id'] != source['id']:
                    relationships.append({'source':source['id'],'target':other['id'],'kind':'reference','label':'Referencia'})
                    break
    unique = {(r['source'],r['target'],r['kind']):r for r in relationships}
    identity={'schema_version':SCHEMA_VERSION,'sources':[(s['path'],s['digest']) for s in sorted(sources,key=lambda s:s['path'])],'nodes':nodes,'relations':list(unique.values())}
    digest = sha256(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'schema_version':SCHEMA_VERSION,'digest':digest,'sources':sources,'nodes':nodes,'relations':list(unique.values()),
            'coverage':{'source_count':len(sources),'bytes':total_bytes,'partial':bool(warnings),'warnings':warnings,
                        'global_skills':'Não configuradas','runtime':'Sem conector de execução'}}
