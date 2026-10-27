/* Mapa explicativo local. Nenhuma seleção dispara rede, modelo ou execução. */
(() => {
  'use strict';
  const root = document.querySelector('[data-brain]');
  if (!root) return;
  const nodes = [...root.querySelectorAll('[data-node]')];
  const details = [...root.querySelectorAll('[data-detail]')];
  const count = root.querySelector('[data-step-count]');
  const announcement = root.querySelector('[data-announcement]');
  const presentation = root.querySelector('[data-presentation]');
  const controls = root.querySelector('[data-tour-controls]');
  const stages = ['coordinator', 'understanding', 'decision', 'plan', 'execution', 'review', 'validation', 'delivery'];
  let current = 'coordinator';
  let presenting = false;

  function select(key, { announce = true, scroll = false } = {}) {
    const selected = details.find(item => item.dataset.detail === key);
    if (!selected) return;
    current = key;
    details.forEach(item => { item.hidden = item !== selected; });
    nodes.forEach(node => {
      if (node.dataset.node === key) node.setAttribute('aria-current', 'step');
      else node.removeAttribute('aria-current');
    });
    const index = stages.indexOf(key);
    count.textContent = index > 0 ? `Etapa ${index} de 7` : index === 0 ? 'Visão geral' : 'Camada de apoio';
    if (announce) announcement.textContent = `${count.textContent}. ${selected.querySelector('h3').textContent}`;
    if (scroll && window.matchMedia('(max-width: 1180px)').matches) {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      root.querySelector('.central-inspector').scrollIntoView({ block: 'nearest', behavior: reduced ? 'instant' : 'smooth' });
    }
  }

  function setPresentation(value) {
    presenting = value;
    document.body.classList.toggle('central-presenting', value);
    presentation.setAttribute('aria-pressed', String(value));
    presentation.querySelector('span').textContent = value ? 'Sair da apresentação' : 'Apresentar fluxo';
    if (value) root.scrollIntoView({ block: 'start', behavior: 'instant' });
    else presentation.focus({ preventScroll: true });
    announcement.textContent = value ? 'Modo apresentação. Use os controles para percorrer as etapas. Escape retorna à visão normal.' : 'Apresentação encerrada.';
  }

  root.addEventListener('click', event => {
    const node = event.target.closest('[data-node]');
    if (node && root.contains(node)) {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      select(node.dataset.node, { scroll: true });
      return;
    }
    if (event.target.closest('[data-presentation]')) setPresentation(!presenting);
    else if (event.target.closest('[data-tour-overview]')) select('coordinator');
    else if (event.target.closest('[data-tour-prev]')) {
      const index = stages.indexOf(current);
      select(stages[index <= 0 ? stages.length - 1 : index - 1]);
    } else if (event.target.closest('[data-tour-next]')) {
      const index = stages.indexOf(current);
      select(stages[(index + 1) % stages.length]);
    }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && presenting) {
      setPresentation(false);
      return;
    }
    if (!presenting || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const index = Math.max(0, stages.indexOf(current));
      const direction = event.key === 'ArrowRight' ? 1 : -1;
      select(stages[(index + direction + stages.length) % stages.length]);
    }
  });

  root.classList.add('is-enhanced');
  presentation.hidden = false;
  controls.hidden = false;
  const fragment = window.location.hash.replace('#detail-', '');
  select(details.some(item => item.dataset.detail === fragment) ? fragment : 'coordinator', { announce: false });
})();
