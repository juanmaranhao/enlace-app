(() => {
  const opener=document.querySelector('[data-directory-open]');if(!opener)return;
  const ui=window.EnlaceUI,dialog=document.getElementById('directoryDialog');let path=null,url=opener.dataset.directoryUrl;
  async function load(nextUrl) {
    const status=dialog.querySelector('[data-directory-status]');status.textContent='Carregando pastas…';
    try {
      const response=await fetch(nextUrl,{headers:{Accept:'application/json'}});if(!response.ok)throw new Error();
      const data=await response.json();path=data.path;dialog.querySelector('[data-directory-path]').textContent=path||'Raízes autorizadas';
      const list=dialog.querySelector('[data-directory-list]');list.replaceChildren();
      for(const directory of data.directories){const button=ui.element('button',{type:'button'},directory.name);button.prepend(ui.icon('folder'));button.addEventListener('click',()=>load(directory.browse_url));list.append(button);}
      dialog.querySelector('[data-directory-select]').disabled=!path;status.textContent=data.directories.length?'':'Sem subpastas disponíveis.';
    } catch {status.textContent='Não foi possível listar a pasta. Confira o acesso ou informe o caminho no formulário.';}
  }
  opener.addEventListener('click',()=>{ui.open(dialog,opener);load(url);});
  dialog.querySelector('[data-directory-roots]').addEventListener('click',()=>load(url));
  dialog.querySelector('[data-directory-select]').addEventListener('click',()=>{if(path){document.getElementById('id_root').value=path;ui.close();}});
})();
