/* Camada comum: diálogos nativos, foco e lock de rolagem compartilhados. */
(() => {
  'use strict';
  let current=null, trigger=null;
  function close() { if(current?.open)current.close(); }
  function open(dialog,button) {
    const preserved=current?.contains(button)?trigger:null;
    if(current?.open)current.close();
    current=dialog;trigger=preserved||button||document.activeElement;
    document.documentElement.classList.add('is-dialog-open');document.body.classList.add('is-dialog-open');
    dialog.showModal();
  }
  function element(tag,attributes={},text='') {
    const node=document.createElement(tag);
    for(const [name,value] of Object.entries(attributes))node.setAttribute(name,String(value));
    if(text)node.textContent=text;
    return node;
  }
  function icon(name) {
    const template=document.querySelector('.el-icon use');
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('class','el-icon');svg.setAttribute('aria-hidden','true');
    const use=document.createElementNS('http://www.w3.org/2000/svg','use');
    use.setAttribute('href',(template?.getAttribute('href')||'').split('#')[0]+'#'+name);svg.append(use);return svg;
  }
  function link(url,label,className='el-textbutton') {
    const target=new URL(url,location.origin);
    if(target.origin!==location.origin||!['http:','https:'].includes(target.protocol))throw new Error('Destino incompatível.');
    return element('a',{href:target.pathname+target.search+target.hash,class:className},label);
  }
  document.querySelectorAll('dialog').forEach(dialog=>{
    dialog.addEventListener('close',()=>{
      if(current===dialog){current=null;document.documentElement.classList.remove('is-dialog-open');document.body.classList.remove('is-dialog-open');if(trigger?.isConnected)trigger.focus({preventScroll:true});}
    });
    dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  });
  document.addEventListener('click',event=>{if(event.target.closest('[data-dialog-close]'))close();});
  window.EnlaceUI={open,close,element,icon,link};
})();
