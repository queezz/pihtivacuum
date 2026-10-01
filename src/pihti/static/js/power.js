(async function () {
  const host = document.getElementById('power-drawing');
  const status = document.getElementById('power-status');
  const save = document.getElementById('power-save');
  let recorded, state, dirty = false;
  const controls = [];
  function paint() {
    controls.forEach(el => {
      const value = state[el.id];
      if (el.id === 'cathode-water') {
        const color = value === 'on' ? '#35aaff' : '#66727d';
        host.querySelector('#cathode-water-pipes').setAttribute('fill', color);
        host.querySelector('#water-valve').setAttribute('fill', color);
        host.querySelector('#water-label').textContent = 'WATER ' + (value ? value.toUpperCase() : '—');
      }
      const active = value === 'on' || value === 'plugged';
      const icon = el.querySelector('use');
      if (icon) {
        icon.style.color = active ? '#36be82' : '#89939d';
        if (el.id.endsWith('-plug-switch')) icon.setAttribute('href', value === 'plugged' ? '#plug-connected-icon' : '#plug-disconnected-icon');
      }
      el.style.opacity = value ? '1' : '.65';
      el.style.cursor = 'pointer';
      const box = el.querySelector('rect');
      if (box) box.setAttribute('stroke-dasharray', value ? '' : '3 3');
      if (el.id.endsWith('-gauge')) {
        if (box) box.setAttribute('fill', active ? '#36be82' : '#c5cbd0');
        const knob = el.querySelector('circle');
        if (knob) { const x = Number(box.getAttribute('x')); knob.setAttribute('cx', x + (active ? 57 : 15)); }
      }
      const label = el.dataset.name + ': ' + (value || 'unrecorded');
      el.setAttribute('aria-label', label);
      const title = el.querySelector('title');
      if (title) title.textContent = label;
    });
    save.disabled = !dirty;
    status.textContent = dirty ? 'Unsaved changes' : 'No unsaved changes';
    document.getElementById('power-recorded').textContent = recorded.timestamp ? new Date(recorded.timestamp).toLocaleString() : 'No snapshot recorded';
  }
  try {
    const [svg, response] = await Promise.all([
      fetch('/static/power.svg?v=' + encodeURIComponent(document.body.dataset.assetVersion)).then(r => { if (!r.ok) throw Error('Diagram unavailable'); return r.text(); }),
      fetch('/power/state').then(r => { if (!r.ok) throw Error('State unavailable'); return r.json(); })
    ]);
    recorded = response; state = {...recorded.state}; host.innerHTML = svg;
    host.querySelector('svg').style.width = '100%'; host.querySelector('svg').removeAttribute('role');
    const names = {anode:'Anode',preanode:'Preanode',cathode:'Cathode',target:'Sputtering target',controlunit:'ControlUnit','instrument-box':'Baratrons / MFCs','ni-logger':'NI logger','langmuir-supplies':'Langmuir supplies','plasma-ig':'Plasma ion gauge','qms-ig':'QMS ion gauge','single-gauge':'SingleGauge'};
    names['membrane-heater'] = 'Membrane heater'; names['cathode-water'] = 'Cathode cooling water';
    Object.keys(names).forEach(name => {
      (name === 'cathode-water' ? [''] : ['-power-switch','-plug-switch','-power','-gauge']).forEach(suffix => {
        const el = host.querySelector('#' + name + suffix); if (!el) return;
        controls.push(el); el.dataset.name = names[name] + (suffix.includes('plug') ? ' plug' : suffix === '-gauge' ? ' gauge' : ' power');
        el.setAttribute('role','button'); el.setAttribute('tabindex','0');
        function toggle() {
          const plugged = suffix.includes('plug'); const on = plugged ? 'plugged' : 'on';
          state[el.id] = state[el.id] === on ? (plugged ? 'unplugged' : 'off') : on;
          const power = controls.find(control => control.id === name + '-power-switch' || control.id === name + '-power');
          const plug = controls.find(control => control.id === name + '-plug-switch');
          const gauge = controls.find(control => control.id === name + '-gauge');
          if (state[el.id] === 'on') { if (plug) state[plug.id] = 'plugged'; if (power) state[power.id] = 'on'; }
          if (state[el.id] === 'unplugged' || (!plugged && suffix !== '-gauge' && state[el.id] === 'off')) {
            if (power) state[power.id] = 'off'; if (gauge) state[gauge.id] = 'off';
          }
          dirty = true; paint();
        }
        el.addEventListener('click',toggle); el.addEventListener('keydown',event => { if (event.key === 'Enter' || event.key === ' ') {event.preventDefault();toggle();} });
      });
    });
    paint();
    save.addEventListener('click', async () => {
      save.disabled = true;
      try { const r = await fetch('/power/state', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state,base_timestamp:recorded.timestamp})}); const data = await r.json(); if (!r.ok) throw Error(data.error); recorded = data; state = {...data.state}; dirty = false; paint(); }
      catch (error) {status.textContent = error.message;save.disabled = false;}
    });
    document.getElementById('power-discard').addEventListener('click', () => {state = {...recorded.state};dirty = false;paint();});
    window.addEventListener('beforeunload', event => {if (dirty) {event.preventDefault();event.returnValue = '';}});
  } catch(error) {status.textContent = error.message;}
})();
