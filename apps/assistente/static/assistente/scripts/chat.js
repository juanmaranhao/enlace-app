(() => {
  'use strict';const dialog=document.getElementById('chatDialog');if(!dialog)return;
  const ui=window.EnlaceUI,form=dialog.querySelector('[data-chat-form]'),input=form.elements.question,messages=dialog.querySelector('[data-chat-messages]');
  let context=null,busy=false,conversationId=crypto.randomUUID();
  dialog.querySelector('[data-chat-all]')?.addEventListener('change',()=>{conversationId=crypto.randomUUID();messages.replaceChildren(ui.element('p',{class:'el-caption'},'Escopo alterado. Uma nova conversa começa aqui.'));});
  document.addEventListener('enlace:context',event=>{context=event.detail;});
  document.addEventListener('click',event=>{const button=event.target.closest('[data-chat-open]');if(button){ui.open(dialog,button);input.focus();if(context){input.placeholder=`Pergunte sobre ${context.name}…`;dialog.querySelector('[data-selected-context]').textContent=`Elemento selecionado: ${context.name} · versão ${context.snapshot_id.slice(0,8)}`;}}});
  dialog.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{input.value=button.dataset.question;form.requestSubmit();}));
  form.addEventListener('submit',async event=>{
    event.preventDefault();const question=input.value.trim();if(!question||busy)return;busy=true;form.querySelector('button').disabled=true;
    messages.append(ui.element('div',{class:'el-userbubble'},question));input.value='';
    const answer=ui.element('div',{class:'el-answer',role:'status'},'Consultando fontes locais…');messages.append(answer);
    try{
      const all=dialog.querySelector('[data-chat-all]')?.checked;
      const response=await fetch(dialog.dataset.messageUrl,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':form.elements.csrfmiddlewaretoken.value},body:JSON.stringify({question,conversation_id:conversationId,request_id:crypto.randomUUID(),mode:dialog.querySelector('[data-chat-ai]')?.checked?'ai':'local',project_id:all?null:dialog.dataset.project||null,selection:context&&!all?{id:context.id,snapshot_id:context.snapshot_id}:null})});
      if(response.redirected)throw new Error('Sua sessão terminou. Entre novamente no Enlace.');
      let data=await response.json();if(!response.ok)throw new Error(data.error||'Não foi possível consultar.');
      const pollUrl=data.poll_url;
      for(let attempt=0;['queued','running'].includes(data.status)&&attempt<60;attempt++){
        answer.textContent=data.status==='queued'?'Na fila do assistente. Aguardando o worker…':'Conversa IA em andamento…';
        await new Promise(resolve=>setTimeout(resolve,2000));
        const status=await fetch(pollUrl,{credentials:'same-origin'});if(!status.ok||status.redirected)throw new Error('Não foi possível acompanhar a mensagem.');data=await status.json();
      }
      answer.textContent=data.error||(['queued','running'].includes(data.status)?'Segue em processamento. Retome pelo ID da conversa.':data.message);
      if(data.mode==='ai_advisory')answer.append(ui.element('small',{class:'el-caption'},' Aconselhamento IA · citações conferidas por ID e trecho; apoio semântico requer revisão.'));
      for(const result of data.results||[]){const card=ui.element('article',{class:'el-chatproject'});card.append(ui.element('h3',{},`${result.project} · ${result.name}`),ui.element('span',{class:'el-badge'},result.kind==='flow'?'Fluxo declarado':result.kind==='skill'?'Skill catalogada':'Referência'),ui.element('p',{},result.excerpt));const actions=ui.element('div',{class:'el-row'});actions.append(ui.link(result.map_url,'Explorar mapa'),ui.link(result.source_url,'Ver fonte'),ui.link(`/projetos/${result.project_id}/analise/?goal=${encodeURIComponent(question)}`,'Avaliar objetivo'));card.append(actions);messages.append(card);}
      if(data.citations?.length){const sources=ui.element('details');sources.append(ui.element('summary',{},'Trechos citados'));for(const citation of data.citations)sources.append(ui.element('p',{},citation.quote));messages.append(sources);}
      dialog.querySelector('[data-conversation-id]').textContent=`Conversa ${conversationId}`;
    }catch(error){answer.textContent=error.message||'A consulta falhou. Tente novamente.';}
    finally{busy=false;form.querySelector('button').disabled=false;input.focus();answer.scrollIntoView({block:'nearest'});}
  });
})();
