function pihtiPowerTransition(state, item, config) {
  const next = {...state, [item.id]: item.status};
  const own = config.find(entry => entry.id === item.id);
  const related = config.filter(entry => entry.device === own.device);
  if (item.status === 'active' && ['power','filament'].includes(own.kind)) {
    related.filter(entry => ['power','plug'].includes(entry.kind)).forEach(entry => {next[entry.id] = 'active';});
  }
  if (item.status === 'inactive' && ['power','plug'].includes(own.kind)) {
    related.filter(entry => ['power','filament'].includes(entry.kind)).forEach(entry => {next[entry.id] = 'inactive';});
  }
  return next;
}
if (typeof module !== 'undefined') module.exports = {pihtiPowerTransition};
if (typeof document !== 'undefined') (async function () {
  const host = document.getElementById('power-drawing');
  if (!host) return;
  const historical = Boolean(window.powerHistory);
  const status = document.getElementById('power-status');
  const toggle = document.getElementById('practice-toggle');
  let recorded = {}, state = {}, config = [], identified = false, busy = false;
  let practice = false, presses = [], deadline = 0, seconds = 180;
  const controls = [];
  const draftKey = 'pihtiPowerPractice';
  function message(text) {if (status) status.textContent = text;}
  function paint() {
    const cards = {anode:'anode-psu', preanode:'preanode-psu', cathode:'kikusui', target:'target-bias-psu'};
    config.filter(entry => entry.kind === 'power').forEach(entry => {
      const card = host.querySelector('#' + (cards[entry.device] || entry.device) + ' > rect.device');
      if (card) {
        const plug = config.find(item => item.device === entry.device && item.kind === 'plug');
        card.parentElement.classList.toggle('device-unplugged', Boolean(plug && state[plug.id] === 'inactive'));
        const on = state[entry.id] === 'active';
        const filamentOff = config.some(item => item.device === entry.device && item.kind === 'filament') && state[entry.device + '-gauge'] !== 'active';
        card.style.fill = on ? filamentOff ? '#233f58' : '#234b40' : '';
        card.style.stroke = on ? filamentOff ? '#35aaff' : '#36be82' : '';
      }
    });
    controls.forEach(el => {
      const own = config.find(entry => entry.id === el.id);
      const value = state[el.id];
      const active = value === 'active';
      const interactive = !historical && identified;
      el.style.cursor = interactive ? 'pointer' : 'default';
      el.setAttribute('aria-disabled', String(!interactive));
      if (interactive) el.setAttribute('tabindex','0'); else el.removeAttribute('tabindex');
      el.style.opacity = value ? '1' : '.65';
      const color = active ? '#36be82' : '#89939d';
      const icon = el.querySelector('use');
      if (icon) {
        icon.style.color = color;
        if (own.kind === 'plug') icon.setAttribute('href', active ? '#plug-connected-icon' : '#plug-disconnected-icon');
      }
      const box = el.querySelector('rect');
      if (box) box.setAttribute('stroke-dasharray', value ? '' : '3 3');
      if (own.kind === 'filament') {
        box.setAttribute('fill', active ? '#36be82' : '#c5cbd0');
        el.querySelector('circle').setAttribute('cx', Number(box.getAttribute('x')) + (active ? Number(box.getAttribute('width')) - 12 : 12));
      }
      if (own.kind === 'water') {
        const water = active ? '#35aaff' : '#66727d';
        box.setAttribute('fill', value ? active ? '#a8ddff' : '#25323d' : '#283440');
        box.setAttribute('stroke', value ? active ? '#35aaff' : '#a5b1bc' : '#758797');
        const waterLabel = host.querySelector('#water-label');
        waterLabel.style.fill = active ? '#172b3a' : '#e0e6ed';
        host.querySelector('#cathode-water-pipes').setAttribute('fill', water);
        const valve = host.querySelector('#water-valve');
        valve.setAttribute('fill', water);
        valve.setAttribute('stroke', active ? '#28465b' : '#a5b1bc');
        waterLabel.textContent = 'WATER ' + (value ? active ? 'ON' : 'OFF' : '—');
      }
      const label = own.label + ': ' + (value ? own.kind === 'plug' ? active ? 'plugged' : 'unplugged' : active ? 'on' : 'off' : 'unrecorded');
      el.setAttribute('aria-label',label);
      el.querySelector('title').textContent = label;
    });
    if (historical) return;
    toggle.disabled = !identified || busy;
    toggle.checked = practice;
    document.getElementById('practice-actions').hidden = !practice;
    ['practice-save','practice-undo','practice-discard'].forEach(id => {document.getElementById(id).disabled = !identified || busy || !presses.length;});
    document.getElementById('practice-save').textContent = presses.length ? `Save ${presses.length} press${presses.length === 1 ? '' : 'es'} to history` : 'Save to history';
    message(!identified ? 'Read only. Choose an operator to record changes.' : practice ? 'Practising. History waits for Save.' : 'Presses are recorded in Power history as you make them.');
    document.getElementById('power-recorded').textContent = recorded.timestamp || 'No changes recorded';
    try {
      if (practice && presses.length) sessionStorage.setItem(draftKey, JSON.stringify({presses,deadline}));
      else sessionStorage.removeItem(draftKey);
    } catch (_) {}
  }
  async function request(url, payload) {
    const response = await fetch(url, payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) {if (response.status === 428) identified = false; const error = Error(result.error || 'Recording failed'); error.result = result; throw error;}
    return result;
  }
  function rebuild() {
    state = {...recorded.state};
    presses.forEach(item => {state = pihtiPowerTransition(state,item,config);});
  }
  async function save(auto=false, acknowledge=false) {
    if (busy || !identified || !presses.length) return;
    busy = true; paint();
    try {
      recorded = await request('/power/practice/save',{presses,auto,acknowledge_warnings:acknowledge});
      state = {...recorded.state}; presses = []; deadline = 0;
      busy = false; paint();
    } catch(error) {
      busy = false; deadline = 0; paint(); message(error.message);
      if (!auto && error.result?.warnings?.length && window.confirm(error.message + '\nRecord this sequence after reviewing the warning?')) save(false,true);
    }
  }
  try {
    const version = encodeURIComponent(document.body.dataset.assetVersion);
    const [svg, entries, snapshot, user, settings] = await Promise.all([
      fetch('/static/power.svg?v='+version).then(r=>{if(!r.ok) throw Error('Diagram unavailable');return r.text();}),
      request('/static/powerControls.json?v='+version),
      historical ? Promise.resolve({state:{}}) : request('/power/state'),
      historical ? Promise.resolve({is_identified:false}) : request('/get_current_user'),
      historical ? Promise.resolve({}) : request('/practice/settings')
    ]);
    host.innerHTML = svg; config = entries; recorded = snapshot; state = {...snapshot.state};
    identified = user.is_identified; seconds = settings.autosave_seconds || 180;
    host.querySelector('svg').style.width = '100%'; host.querySelector('svg').removeAttribute('role');
    config.forEach(own => {
      const el = host.querySelector('#'+own.id); if (!el) return;
      controls.push(el); el.setAttribute('role','button');
      el.style.pointerEvents = 'all';
      el.querySelectorAll('use').forEach(icon => {icon.style.pointerEvents = 'none';});
      async function press() {
        if (historical || !identified || busy) return;
        const item = {id:own.id,status:state[own.id] === 'active' ? 'inactive' : 'active'};
        busy = true;
        if (practice) {
          presses.push(item); state = pihtiPowerTransition(state,item,config);
          deadline = Date.now() + seconds*1000; busy=false; paint(); return;
        }
        try {recorded = await request('/power/update',item); state = {...recorded.state};busy=false;paint();}
        catch(error) {
          busy=false;
          if (error.result?.requires_practice) {practice=true;presses.push(item);state=pihtiPowerTransition(state,item,config);deadline=0;}
          paint();message(error.message);
        }
      }
      el.addEventListener('click',press);
      el.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();press();}});
    });
    if (historical) {
      const container = document.getElementById('diagram-container');
      container.dataset.paint = 'ready'; container.setAttribute('aria-busy','false');
      window.pihtiElementName = id => config.find(entry=>entry.id===id)?.label || '';
      window.applyState = value => {state = {...value};paint();};
      window.pihtiDiagramReady = true;
      document.querySelector('.diagram-load-status')?.remove();
      document.dispatchEvent(new Event('pihti:diagram-ready')); paint(); return;
    }
    // Old snapshot drafts are not silently committed by the new click flow.
    try {
      const draft = JSON.parse(sessionStorage.getItem(draftKey) || 'null');
      if (identified && Array.isArray(draft?.presses) && draft.presses.every(item=>config.some(entry=>entry.id===item.id)&&['active','inactive'].includes(item.status))) {
        practice = true; presses = draft.presses; deadline = Number(draft.deadline)||0; rebuild();
      }
    } catch (_) {}
    toggle.addEventListener('change',()=>{
      if (!identified || busy) return;
      if (presses.length && !window.confirm('Leave Practice and discard these presses?')) {toggle.checked=true;return;}
      practice = toggle.checked; presses=[];deadline=0;state={...recorded.state};paint();
    });
    document.getElementById('practice-save').addEventListener('click',()=>save());
    document.getElementById('practice-undo').addEventListener('click',()=>{if(!identified||busy)return;presses.pop();rebuild();deadline=presses.length?Date.now()+seconds*1000:0;paint();});
    document.getElementById('practice-discard').addEventListener('click',()=>{if(!identified||busy)return;presses=[];deadline=0;state={...recorded.state};paint();});
    setInterval(()=>{
      const timer=document.getElementById('practice-timer');
      const left=Math.max(0,Math.ceil((deadline-Date.now())/1000));
      timer.textContent=presses.length&&deadline?`Saves itself in ${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}.`:'';
      if(practice&&presses.length&&deadline&&left===0&&!busy) save(true);
    },1000);
    setInterval(async()=>{
      if(busy||practice)return;
      try {const [latest,identity]=await Promise.all([request('/power/state'),request('/get_current_user')]);if(busy||practice)return;recorded=latest;state={...latest.state};identified=identity.is_identified;paint();}
      catch(error){message(error.message);}
    },5000);
    paint();
  } catch(error) {message(error.message);}
})();
