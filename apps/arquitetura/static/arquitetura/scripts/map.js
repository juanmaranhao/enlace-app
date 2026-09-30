/* Relações declaradas. Selecionar não executa nem reordena o fluxo. */
(() => {
  'use strict';
  const raw=document.getElementById('graph-data'), root=document.querySelector('[data-map]');
  if(!raw||!root)return;
  const graph=JSON.parse(raw.textContent), ui=window.EnlaceUI;
  const stage=root.querySelector('[data-stage]'), svg=stage.querySelector('svg');
  const bar=document.querySelector('[data-selection]'), dialog=document.getElementById('inspector');
  const kinds={flow:'Fluxo',skill:'Skill',agent:'Agente',rule:'Regra',contract:'Contrato',guide:'Guia'};
  const icons={flow:'workflow',skill:'sparkles',agent:'activity',rule:'shield',contract:'lock',guide:'file'};
  const stateKey=`enlace-map:${root.dataset.project}:${graph.snapshot_id}:${graph.anchor?.id}`;
  let saved={};try{saved=JSON.parse(sessionStorage.getItem(stateKey)||'{}');}catch{}
  const buttons=new Map();let selected=null,showSupport=!!saved.support,zoom=saved.zoom||'reset',requestSerial=0;
  const viewport=root.querySelector('.el-mapviewport');
  function remember(){try{sessionStorage.setItem(stateKey,JSON.stringify({selected:selected?.id,support:showSupport,zoom,left:viewport.scrollLeft,top:viewport.scrollTop}));}catch{}}
  function sourceUrl(url){return `${url}?focus=${encodeURIComponent(graph.anchor?.id||'')}`;}
  for(const node of graph.nodes){
    const button=ui.element('button',{type:'button',class:'el-node','data-node-id':node.id,'aria-pressed':'false'});
    const badge=ui.element('small',{},kinds[node.kind]||node.kind);badge.prepend(ui.icon(icons[node.kind]||'file'));
    button.append(badge,ui.element('strong',{},node.name));
    button.classList.toggle('is-support',node.support);button.addEventListener('click',()=>select(node));
    stage.append(button);buttons.set(node.id,button);
  }
  function connected(id){const ids=new Set([id]);for(const edge of graph.relations)if(edge.source===id||edge.target===id){ids.add(edge.source);ids.add(edge.target);}return ids;}
  function select(node){
    selected=node;const near=connected(node.id);
    for(const [id,button] of buttons){button.classList.toggle('is-selected',id===node.id);button.classList.toggle('is-near',id!==node.id&&near.has(id));button.classList.toggle('is-muted',!near.has(id));button.setAttribute('aria-pressed',String(id===node.id));}
    bar.hidden=false;bar.querySelector('[data-selected-name]').textContent=node.name;
    bar.querySelector('[data-selected-source]').href=sourceUrl(node.source_url);
    document.dispatchEvent(new CustomEvent('enlace:context',{detail:{id:node.id,snapshot_id:graph.snapshot_id,name:node.name,kind:node.kind}}));draw();remember();
  }
  function visible(){for(const node of graph.nodes)buttons.get(node.id).hidden=node.support&&!showSupport&&node.id!==graph.anchor?.id;draw();}
  function draw(){
    svg.replaceChildren();svg.setAttribute('viewBox',`0 0 ${stage.offsetWidth} ${stage.offsetHeight}`);
    for(const edge of graph.relations){
      const a=buttons.get(edge.source),b=buttons.get(edge.target);if(!a||!b||a.hidden||b.hidden)continue;
      const ax=a.offsetLeft+a.offsetWidth/2,ay=a.offsetTop+a.offsetHeight/2,bx=b.offsetLeft+b.offsetWidth/2,by=b.offsetTop+b.offsetHeight/2;
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d',`M ${ax} ${ay} C ${ax} ${(ay+by)/2} ${bx} ${(ay+by)/2} ${bx} ${by}`);
      if(selected)path.setAttribute('class',edge.source===selected.id||edge.target===selected.id?'is-lit':'is-muted');
      svg.append(path);
    }
  }
  function supportLabel(){const button=document.querySelector('[data-support]');if(button){button.setAttribute('aria-pressed',String(showSupport));button.querySelector('span').textContent=showSupport?'Ocultar apoio':'Mostrar apoio';}}
  document.querySelector('[data-support]')?.addEventListener('click',()=>{showSupport=!showSupport;supportLabel();visible();remember();});
  function setZoom(){stage.classList.toggle('el-zoomout',zoom==='out');stage.classList.toggle('el-zoomin',zoom==='in');draw();}
  root.querySelectorAll('[data-zoom]').forEach(button=>button.addEventListener('click',()=>{zoom=button.dataset.zoom;setZoom();remember();}));
  viewport.addEventListener('scroll',remember,{passive:true});
  const elementPanel=dialog.querySelector('[data-element-panel]'),flowPanel=dialog.querySelector('[data-flow-panel]'),status=dialog.querySelector('[data-inspector-status]');
  function tab(name){dialog.querySelectorAll('[data-inspector-tab]').forEach(button=>{const active=button.dataset.inspectorTab===name;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});elementPanel.hidden=name!=='element';flowPanel.hidden=name!=='flow';}
  const tabs=[...dialog.querySelectorAll('[data-inspector-tab]')];
  tabs.forEach((button,index)=>{button.addEventListener('click',()=>tab(button.dataset.inspectorTab));button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?1:1-index;tab(tabs[next].dataset.inspectorTab);tabs[next].focus();}});});
  document.querySelector('[data-inspect]').addEventListener('click',async event=>{
    if(!selected)return;const serial=++requestSerial;
    dialog.querySelector('#inspectorTitle').textContent=selected.name;dialog.querySelector('[data-node-kind]').textContent=kinds[selected.kind];
    elementPanel.replaceChildren();flowPanel.replaceChildren();status.textContent='Carregando fonte…';tab('element');ui.open(dialog,event.currentTarget);
    try{
      const response=await fetch(selected.inspect_url,{credentials:'same-origin'});if(!response.ok)throw new Error();
      const data=await response.json();if(serial!==requestSerial)return;
      elementPanel.append(ui.element('p',{},data.node.summary||'Sem descrição resumida na fonte.'));
      const details=ui.element('details');details.append(ui.element('summary',{},'Ver detalhes e fonte'),ui.element('pre',{class:'el-code'},data.source.excerpt),ui.link(sourceUrl(data.source.url),data.source.excerpt_partial?'Abrir fonte completa':'Abrir fonte registrada'));elementPanel.append(details);
      flowPanel.append(ui.element('p',{},`${data.related.length} conexões declaradas. Elas indicam referências; a ordem de execução depende das instruções de cada fonte.`));
      const operation=ui.element('div',{class:'el-steps'}),support=ui.element('details');support.append(ui.element('summary',{},'Pastas, regras e contratos de apoio'));
      for(const node of data.related){const row=ui.element('div',{class:'el-step'});row.append(ui.icon(icons[node.kind]||'file'));const content=ui.element('div');content.append(ui.element('strong',{},node.name),ui.element('p',{},node.summary),ui.link(`${root.dataset.mapUrl}?snapshot=${graph.snapshot_id}&focus=${node.id}`,'Explorar conexões'));row.append(content);(node.kind==='flow'||node.kind==='skill'?operation:support).append(row);}
      flowPanel.append(operation,support);status.textContent=`${data.source.path} · snapshot ${graph.snapshot_id.slice(0,8)}`;
    }catch{if(serial===requestSerial)status.textContent='Não foi possível abrir os detalhes. Use a alternativa textual abaixo do mapa.';}
  });
  new ResizeObserver(draw).observe(stage);supportLabel();visible();setZoom();
  if(saved.selected){const node=graph.nodes.find(n=>n.id===saved.selected);if(node)select(node);}
  viewport.scrollLeft=saved.left||0;viewport.scrollTop=saved.top||0;
})();
