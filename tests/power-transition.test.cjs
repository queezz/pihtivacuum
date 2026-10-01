const {test}=require('node:test');
const assert=require('node:assert/strict');
const {pihtiPowerTransition}=require('../src/pihti/static/js/power.js');
const config=require('../src/pihti/static/powerControls.json');
test('filament on powers and plugs the controller; unplug shuts both off',()=>{
 const initial={};
 const on=pihtiPowerTransition(initial,{id:'plasma-ig-gauge',status:'active'},config);
 assert.deepEqual(initial,{});
 assert.equal(on['plasma-ig-power'],'active');assert.equal(on['plasma-ig-plug-switch'],'active');
 const off=pihtiPowerTransition(on,{id:'plasma-ig-plug-switch',status:'inactive'},config);
 assert.equal(off['plasma-ig-power'],'inactive');assert.equal(off['plasma-ig-gauge'],'inactive');
 assert.equal(on['plasma-ig-power'],'active');
});
test('water remains independent; SingleGauge has no filament control',()=>{
 const state={'cathode-power-switch':'active'};
 assert.deepEqual(pihtiPowerTransition(state,{id:'cathode-water',status:'inactive'},config),{...state,'cathode-water':'inactive'});
 assert.ok(!config.some(item=>item.id==='single-gauge-gauge'));
});
