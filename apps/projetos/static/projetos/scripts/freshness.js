(() => {
  'use strict';const marker=document.querySelector('[data-freshness]');if(!marker)return;
  let timer=null;
  async function check(){
    if(document.hidden)return;
    try{
      const response=await fetch(marker.dataset.statusUrl,{credentials:'same-origin'});if(!response.ok||response.redirected)return;
      const data=await response.json();
      if(data.snapshot_id&&data.snapshot_id!==marker.dataset.snapshot){marker.hidden=false;marker.querySelector('[data-freshness-text]').textContent='Nova versão disponível';}
      else if(['queued','running'].includes(data.status)){marker.hidden=false;marker.querySelector('[data-freshness-text]').textContent=`Leitura ${data.status==='queued'?'na fila':'em andamento'} · ${data.source_count} fontes`;}
      else marker.hidden=true;
    }catch{/* Uma falha de observação não substitui o último snapshot. */}
  }
  timer=setInterval(check,5000);document.addEventListener('visibilitychange',check);window.addEventListener('pagehide',()=>clearInterval(timer));check();
})();
