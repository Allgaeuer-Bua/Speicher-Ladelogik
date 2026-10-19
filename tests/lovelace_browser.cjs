/* Mocked Home Assistant only: never connects to a real controller. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.join(__dirname, '../custom_components/speicher_ladelogik_ae/frontend');
const out = path.join(__dirname, '../dashboard-review');
fs.mkdirSync(out, {recursive:true});

(async()=>{
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}, timezoneId:'Europe/Berlin'});
    const errors=[];
    page.on('pageerror',error=>{errors.push(error.message);console.error('Browser error:',error.stack)});
    await page.route('http://lovelace.test/**',route=>{
      const url=new URL(route.request().url());
      if(url.pathname.endsWith('.js')) {
        const file=path.join(root,path.basename(url.pathname));
        return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(file,'utf8')});
      }
      return route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:14px;background:#f5f7f8"><div id="mount"></div></body></html>'});
    });
    await page.goto('http://lovelace.test/');
    await page.evaluate(async()=>{
      class Icon extends HTMLElement {connectedCallback(){this.style.display='inline-block';this.style.width='18px';this.style.height='18px';}}
      customElements.define('ha-icon',Icon);
      await import('/speicher-ladelogik-ae-card.js?v=test');
      window.calls=[];window.histories=[];window.infos=[];
      document.addEventListener('hass-more-info',event=>window.infos.push(event.detail.entityId));
      const states={},entities={},sources={};
      const set=(key,value,attributes={},domain='sensor')=>{
        const id=`${domain}.test_${key}`;states[id]={entity_id:id,state:String(value),attributes,last_updated:new Date().toISOString()};return id;
      };
      const native=(key,value,attributes={},domain='sensor')=>entities[key]=set(key,value,attributes,domain);
      const source=(key,value,unit,extra={})=>sources[key]=set('source_'+key,value,{unit_of_measurement:unit,...extra},key.includes('_limit_')?'number':'sensor');
      const now=Date.now()/1000;
      const plan={tagesklasse:'stark',fruehes_soc_ziel_tagesklasse:'stark',mittagsspitzen_aktiv:true,mittagsspitzen_planbar:true,
        prognose_rest_erwartet_kwh:43.09,prognose_morgen_kwh:76.89,restbedarf_kwh:3.15,soll_ladeleistung_gesamt_w:2400,
        ladefenster_start_ts:now-3600,ladefenster_ende_ts:now+18000,fenster_fortschritt_prozent:20,
        entscheidungsgrund:'Ladefreigabe bleibt bestehen; AstraMeter regelt',warnungen:[],datenfehler_aktuell:[]};
      const extra={};
      for(const [slot,soc,power,max] of [['a',55,0,1500],['e',75,-533,2500]]){
        source('soc_'+slot,soc,'%');source('power_'+slot,power,'W');source('dc_'+slot,slot==='a'?0:500,'W');
        source('charge_limit_'+slot,slot==='a'?1100:1300,'W',{min:0,max,step:50});source('discharge_limit_'+slot,max,'W',{min:0,max,step:50});
        source('inverter_'+slot,slot==='a'?'Standby':'Charge','');
        source('cell_voltage_'+slot,3.29,'V');source('cell_temp_max_'+slot,24,'°C');source('cell_temp_min_'+slot,23,'°C');
        source('drift_'+slot,3,'mV');
        native('handbetrieb_venus_'+slot,'off',{},'switch');
        for(const [key,value] of [['manuell_laden',0],['manuell_entladen',max],['bevorzugte_ladeleistung',slot==='a'?1100:1300],['maximale_ladeleistung',max],['maximale_entladeleistung',max]])native(key+'_venus_'+slot,value,{min:0,max,step:50,unit_of_measurement:'W'},'number');
        native('daten_venus_'+slot,'bereit');
        for(const cls of ['schwach','wechselhaft','mittel','stark'])native('fruehes_ladeziel_venus_'+slot+'_'+cls,cls==='stark'?0:50,{min:0,max:100,step:1,unit_of_measurement:'%'},'number');
        Object.assign(plan,{['daten_gueltig_venus_'+slot]:true,['fahrplan_slot_aktiv_venus_'+slot]:true,['soll_ladegrenze_venus_'+slot+'_w']:slot==='a'?1100:1300,['ladefreigabe_venus_'+slot+'_seit_ts']:now-3600,['restbedarf_venus_'+slot+'_kwh']:slot==='a'?1.87:1.28,
          ['leistungsentscheidung_venus_'+slot]:{zeit_ts:now,bevorzugt_w:slot==='a'?1100:1300,roh_w:1300,stabil_w:1300,grund:'Ladefreigabe bleibt bestehen',fenster_start_ts:now-3600,simulation_ende_ts:now+18000},['restzeit_venus_'+slot]:{modus:'pausiert',restzeit_s:null}});
        extra[slot+'_mode']=set(slot+'_mode','anti_feed',{options:['anti_feed','manual']},'select');
        extra[slot+'_fan']=set(slot+'_fan','off',{},'switch');
        for(const [key,val,unit] of [['voltage',50,'V'],['current',0,'A'],['mos1',22,'°C'],['mos2',23,'°C'],['temperature',24,'°C'],['load',0,'%'],['usable',2.1,'kWh'],['charge_today',2.69,'kWh'],['discharge_today',3.28,'kWh'],['efficiency',89,'%']])extra[slot+'_'+key]=set(slot+'_'+key,val,{unit_of_measurement:unit});
      }
      sources.pack_soc_a=[set('pack1',55,{unit_of_measurement:'%'}),set('pack2',55,{unit_of_measurement:'%'})];
      sources.drift_a=[sources.drift_a,sources.drift_a];
      for(const p of [1,2])for(let i=1;i<=13;i++)extra[`a_p${p}_cell_${i}`]=set(`p${p}c${i}`,3.28+i*.0001,{unit_of_measurement:'V'});
      native('status','Bereit',{version:'2.3.1',betriebsart:'Automatik',schreibzugriffe_aktiv:true,planung_aktiv:true,quellen_verfuegbar:43,quellen_gesamt:43,warnungen:[],fehlende_entitaeten:[]});
      native('planung','Ladefreigabe aktiv',plan);native('kalibrierung','Bereit',{auftraege:[],phase:'idle'});native('betriebsart','Automatik',{},'select');native('mittagsspitzen','on',{},'switch');
      native('kalibrierung_venus_e_morgen','',{},'button');
      for(const [key,value,unit] of [['prognose_sicherheit',90,'%'],['unplanbare_reserve',1,'kWh'],['ladewirkungsgrad',90,'%'],['planung_hysterese',.2,'kWh'],['knappheitsreserve',125,'%'],['schwacher_tag',20,'kWh'],['mittlerer_tag',50,'kWh'],['starker_tag',85,'kWh'],['mittag_vorlauf',1.5,'h'],['mittag_nachlauf',2,'h'],['kalibrierleistung',500,'W'],['kalibrierung_ruhe_unten',0,'min'],['kalibrierung_ruhe_oben',90,'min']])native(key,value,{min:0,max:2500,step:.1,unit_of_measurement:unit},'number');
      window.entry={entry_id:'test',version:'2.3.1',models:['A','E'],entities,sources};
      window.fixture={states,entities,sources,extra};
      window.hass={states,user:{is_admin:true},themes:{darkMode:false},config:{time_zone:'Europe/Berlin'},
        callWS:async msg=>{if(msg.type==='speicher_ladelogik_ae/config')return {entries:[window.entry]};throw new Error('Unexpected WS command '+msg.type)},
        callApi:async (method,url)=>{window.histories.push(url);return []},
        callService:async (...args)=>{window.calls.push(args);if(window.rejectNext){window.rejectNext=false;throw new Error('Simulierter Schreibfehler')}return {}}
      };
      window.mountCard=(view='overview')=>{
        document.querySelector('#mount').replaceChildren();
        const card=document.createElement('speicher-ladelogik-ae-card');
        card.setConfig({view,theme:'light',entities:extra});
        card.hass=window.hass;document.querySelector('#mount').append(card);window.card=card;return card;
      };
      window.mountCard();
    });
    try { await page.locator('.summary-grid').waitFor({timeout:10000}); }
    catch(error) { console.error(await page.evaluate(()=>window.card?.shadowRoot?.innerHTML?.slice(-4500))); throw error; }
    await page.waitForTimeout(200);
    assert.equal(await page.locator('[data-tab]').count(),0,'No duplicate internal navigation');
    assert.equal(await page.locator('.flow-card').count(),0,'Energy flow removed');
    assert.equal(await page.locator('.battery-card').count(),2);
    assert.equal(await page.locator('.device-controls').count(),2);
    assert.equal(await page.locator('.electrical-details').count(),2);
    assert.match(await page.locator('.summary-status').innerText(),/Stark/);
    assert.match(await page.locator('.summary-status').innerText(),/Ladefreigabe aktiv/);
    assert.deepEqual(await page.evaluate(()=>window.calls),[],'Mounting performs no writes');
    await page.locator('[data-live-battery="a-soc"]').click();
    assert.equal(await page.evaluate(()=>window.infos.at(-1)),await page.evaluate(()=>window.fixture.sources.soc_a));
    await page.locator('[data-battery="a"] .metric[aria-label="Ladegrenze · Entität oder Quellen öffnen"]').click();
    assert.equal(await page.evaluate(()=>window.infos.at(-1)),await page.evaluate(()=>window.fixture.sources.charge_limit_a));
    await page.locator('[data-battery="a"] .detail.value-link').filter({hasText:'Pack-SoC'}).click();
    assert.equal(await page.locator('dialog.value-sources .value-source-row').count(),2,'Composite values list their real sources');
    await page.locator('dialog.value-sources .value-source-row').first().click();
    assert.equal(await page.evaluate(()=>window.infos.at(-1)),await page.evaluate(()=>window.fixture.sources.pack_soc_a[0]));
    await page.locator('[data-battery="a"] .drift-value').first().click();
    assert.equal(await page.evaluate(()=>window.infos.at(-1)),await page.evaluate(()=>window.fixture.sources.drift_a[0]),'Drift chips open their sensor too');
    await page.locator('[data-remember-details="control-a"] summary').click();
    await page.locator('[data-remember-details="electric-a"] summary').click();
    const a=page.locator('[data-manual-form="A"]');
    await a.locator('[data-manual-active]').check();
    await a.locator('[data-manual-range="charge"]').fill('1200');
    await page.evaluate(()=>{window.card.hass={...window.hass,states:{...window.hass.states}}});
    assert.equal(await a.locator('[data-manual-range="charge"]').inputValue(),'1200','Draft survives live update');
    assert.deepEqual(await page.evaluate(()=>window.calls),[],'Editing draft performs no writes');
    await a.locator('[data-apply-manual]').click();
    await page.waitForTimeout(100);
    let calls=await page.evaluate(()=>window.calls);
    assert.deepEqual(calls,[['speicher_ladelogik_ae','apply_manual',{entry_id:'test',battery:'A',active:true,charge_w:1200,discharge_w:1500}]]);
    assert.ok(!JSON.stringify(calls).includes('soc'),'No SoC write');
    // A failed save keeps the draft available and never writes E.
    await page.evaluate(()=>{window.rejectNext=true});
    await a.locator('[data-manual-active]').check();
    await a.locator('[data-manual-range="charge"]').fill('1150');
    await a.locator('[data-apply-manual]').click();
    await page.waitForTimeout(100);
    assert.match(await a.innerText(),/Nicht übernommen/);
    assert.equal(await a.locator('[data-manual-range="charge"]').inputValue(),'1150');
    // Charts retain both custom ranges and chosen view through card renders.
    const main=page.locator('speicher-ladelogik-telemetry');
    const order=await main.evaluate(el=>[...el.shadowRoot.querySelector('.vs-app').children].map(node=>node.className));
    assert.ok(order.indexOf('vs-pack-charts')<order.indexOf('vs-lower'),'Pack charts precede current cells and energy balance');
    assert.equal(await main.locator('.vs-lower > section').first().getAttribute('aria-label'),'Zellspannungen beider Speicher');
    // Identity alone misses detach/reattach: native date pickers also require
    // uninterrupted connection and focus across real HA and timer updates.
    for(const chart of ['main','pack1','pack2'])for(const boundary of ['from','to']){
      const kept=await main.evaluate((el,{chart,boundary})=>{
        const input=el.shadowRoot.querySelector(`#vs-${chart}-${boundary}`),value=input.value;
        let blurred=0;const onBlur=()=>blurred++;
        input.addEventListener('blur',onBlur);input.focus();
        window.card.hass={...window.hass,states:{...window.hass.states}};
        el._update();window.card._render();
        const result={same:input===el.shadowRoot.querySelector(`#vs-${chart}-${boundary}`),connected:input.isConnected,focused:el.shadowRoot.activeElement===input,blurred,unchanged:input.value===value};
        input.removeEventListener('blur',onBlur);input.blur();return result;
      },{chart,boundary});
      assert.deepEqual(kept,{same:true,connected:true,focused:true,blurred:0,unchanged:true},`${chart} ${boundary}: native picker focus retained`);
    }
    await page.evaluate(()=>{
      const id=window.fixture.extra.a_charge_today,next={...window.hass.states,[id]:{...window.hass.states[id],state:'3.5'}};
      window.fixture.states=next;window.hass={...window.hass,states:next};window.card.hass=window.hass;
    });
    await page.waitForTimeout(80);
    assert.match(await main.locator('#vs-energy-rows').innerText(),/3,50/,'Persistent analytics still receive immutable HA state changes');
    await main.locator('[data-view="soc"]').click();
    await main.locator('#vs-main-from').fill('2026-10-17T08:15');
    await main.locator('#vs-main-to').fill('2026-10-17T10:45');
    await main.locator('[data-date-form="main"] button').click();
    await page.evaluate(()=>{window.card.shadowRoot.activeElement?.blur();window.card._render()});
    assert.equal(await main.locator('#vs-main-from').inputValue(),'2026-10-17T08:15');
    assert.equal(await main.locator('[data-view="soc"]').getAttribute('aria-pressed'),'true');
    for(const width of [1280,390,320]){
      await page.setViewportSize({width,height:900});
      for(const view of ['overview','calibration','control','diagnostics']){
        await page.evaluate(view=>window.mountCard(view),view);
        await page.locator('speicher-ladelogik-ae-card main').waitFor();
        await page.waitForTimeout(70);
        const overflow=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:innerWidth,
          cards:[...window.card.shadowRoot.querySelectorAll('.card,.battery-card')].filter(el=>el.scrollWidth>el.clientWidth+2).map(el=>el.className)}));
        assert.ok(overflow.page<=overflow.viewport+2,`${width} ${view}: ${JSON.stringify(overflow)}`);
        assert.deepEqual(overflow.cards,[],`${width} ${view}: card overflow`);
        if(width!==320)await page.screenshot({path:path.join(out,`lovelace-${width}-${view}.png`),fullPage:true});
        if(view==='overview')assert.equal(await page.locator('.plan-card').evaluate(el=>Math.round(el.getBoundingClientRect().width)),await page.locator('main.overview').evaluate(el=>Math.round(el.getBoundingClientRect().width)),'Planning uses full width');
        if(view==='overview'){
          const collisions=await page.locator('.metric').evaluateAll(metrics=>metrics.filter(metric=>{
            const label=metric.querySelector(':scope > span')?.getBoundingClientRect(),value=metric.querySelector(':scope > strong')?.getBoundingClientRect();
            return label&&value&&value.top<label.bottom+2;
          }).map(metric=>metric.textContent));
          assert.deepEqual(collisions,[],`${width}: labels and metric values never overlap`);
          const summaries=await page.evaluate(()=>{
            const root=window.card.shadowRoot,below=(first,second)=>second.getBoundingClientRect().top>=first.getBoundingClientRect().bottom;
            return {ring:below(root.querySelector('.soc-ring strong'),root.querySelector('.soc-ring .value-link>span')),
              energy:below(root.querySelector('[data-summary-energy]'),root.querySelector('[data-summary-reference]')),
              battery:below(root.querySelector('[data-live-battery="a-power"]'),root.querySelector('[data-live-battery="a-mode"]'))};
          });
          assert.deepEqual(summaries,{ring:true,energy:true,battery:true},`${width}: linked summary values keep their line breaks`);
          if(width===390){
            const telemetry=page.locator('speicher-ladelogik-telemetry');
            for(const chart of ['main','pack1','pack2']){
              const layout=await telemetry.evaluate((el,chart)=>{
                const svg=el.shadowRoot.querySelector(`#vs-${chart}-chart svg`),r=svg.getBoundingClientRect();
                svg.dispatchEvent(new PointerEvent('pointerdown',{clientX:r.left+r.width/2,clientY:r.top+70,pointerType:'touch',bubbles:true}));
                const tip=svg.parentNode.querySelector('.vs-tooltip');
                return {below:tip.getBoundingClientRect().top>=r.bottom+8,position:getComputedStyle(tip).position,visible:!tip.hidden};
              },chart);
              assert.deepEqual(layout,{below:true,position:'static',visible:true},`${chart}: mobile readout is below the plot`);
            }
            await telemetry.locator('#vs-pack1-chart .vs-tooltip .entity-info').first().click();
            assert.equal(await page.evaluate(()=>window.infos.at(-1)),await page.evaluate(()=>window.fixture.extra.a_p1_cell_1),'Chart values open their sensor');
            await page.screenshot({path:path.join(out,'lovelace-390-chart-readout.png'),fullPage:true});
          }
        }
        if(view==='control')assert.equal(await page.locator('[data-manual-form]').count(),0);
      }
    }
    await page.evaluate(()=>{window.hass={...window.hass,user:{is_admin:false}};window.mountCard()});
    await page.locator('.summary-grid').waitFor();
    await page.locator('[data-remember-details="control-a"] summary').click();
    assert.equal(await a.locator('[data-manual-active]').isDisabled(),true);
    await page.evaluate(()=>{window.fixture.states[window.fixture.sources.soc_a]={state:'unavailable',attributes:{}};window.card._render()});
    assert.equal(await page.locator('[data-live-combined]').innerText(),'—','Missing SoC never becomes zero');
    assert.deepEqual(errors,[]);
    console.log('Lovelace browser checks passed: 4 native views; 320/390/1280px; no writes on mount/edit; independent atomic manual action; failed draft; admin guard; retained chart ranges; missing telemetry.');
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
