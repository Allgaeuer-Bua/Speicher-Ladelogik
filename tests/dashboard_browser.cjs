/* Browser smoke checks and review screenshots, using mocked HA states only. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const mdi = require('@mdi/js');
const script = fs.readFileSync(path.join(__dirname, '../custom_components/speicher_ladelogik_ae/frontend/speicher-ladelogik-ae-panel.js'), 'utf8');
const icons = Object.fromEntries([...script.matchAll(/mdi:([a-z0-9-]+)/g)].map(([, name]) => [
  `mdi:${name}`, mdi['mdi' + name.split('-').map(s => s[0].toUpperCase() + s.slice(1)).join('')] || mdi.mdiCircleOutline,
]));
const tag = script.match(/const PANEL_ELEMENT = "([^"]+)"/)[1];
const out = path.join(__dirname, '../dashboard-review');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, timezoneId: 'Europe/Berlin' });
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.clock.setFixedTime(new Date('2026-10-08T10:00:00+02:00'));
    await page.route('http://dashboard.test/**', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0"></body></html>' }));
    async function mount() {
      await page.goto('http://dashboard.test/');
      await page.evaluate(iconPaths => {
        class Icon extends HTMLElement {
          static get observedAttributes() { return ['icon']; }
          connectedCallback() { this.render(); }
          attributeChangedCallback() { this.render(); }
          render() {
            if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
            this.shadowRoot.innerHTML = `<style>:host{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle}svg{width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px);fill:currentColor}</style><svg viewBox="0 0 24 24"><path d="${iconPaths[this.getAttribute('icon')] || ''}"></path></svg>`;
          }
        }
        customElements.define('ha-icon', Icon);
      }, icons);
      await page.addScriptTag({ content: script });
      await page.evaluate(tagName => {
        const p = document.createElement(tagName);
        const states = {}, entities = {}, sources = {};
        const set = (key, value, attributes = {}, domain = 'sensor') => {
          entities[key] = `${domain}.fixture_${key}`;
          states[entities[key]] = { state: String(value), attributes, entity_id: entities[key] };
        };
        const src = (key, value, unit = '') => {
          sources[key] = `sensor.source_${key}`;
          states[sources[key]] = { state: String(value), attributes: { unit_of_measurement: unit }, entity_id: sources[key] };
        };
        const now = Date.now() / 1000;
        const plan = { daten_gueltig_venus_a: true, daten_gueltig_venus_e: true, mittagsspitzen_aktiv: false,
          tagesklasse: 'schwach', fruehe_soc_ziele_prozent: { A: 50, E: 55 }, restbedarf_kwh: 3.15,
          entscheidungsgrund: 'Schwacher Tag: früh laden, keine Mittagsspitzenkappung',
          prognose_rest_erwartet_kwh: 11.93, prognose_morgen_kwh: 88.52,
          prognose_kurzfristfaktor: 0.704, hausleistung_aktuell_w: 1705, ueberschuss_untergrenze_w: 591,
          soll_ladeleistung_gesamt_w: 2600, ladefenster_start_ts: now - 3600, ladefenster_ende_ts: now + 18000,
          mittagsfenster_start_ts: now + 5400, mittagsfenster_ende_ts: now + 18000, sonnenhoechststand_ts: now + 10800,
          warnungen: [], datenfehler_aktuell: [], kalibrierauftraege: [], fenster_fortschritt_prozent: 17 };
        const cal = { auftraege: [], ruhedauer_unten_min: 45, ruhedauer_oben_min: 90,
          phase: 'idle', grund: 'Kein Auftrag aktiv', energie_ac_kwh: 0 };
        for (const [letter, soc, power, preferred, capacity] of [['A', 55, 0, 1100, 4.16], ['E', 75, -555, 1300, 5.12]]) {
          const s = letter.toLowerCase();
          Object.assign(plan, { [`fahrplan_slot_aktiv_venus_${s}`]: true, [`soll_ladegrenze_venus_${s}_w`]: 1300,
            [`ladefreigabe_venus_${s}_seit_ts`]: now - 3600, [`restbedarf_venus_${s}_kwh`]: capacity * (1 - soc / 100),
            [`nennkapazitaet_venus_${s}_kwh`]: capacity, [`ac_leistung_venus_${s}_status`]: 'frisch',
            [`leistungsentscheidung_venus_${s}`]: { zeit_ts: now, bevorzugt_w: preferred, roh_w: 1300, stabil_w: 1300,
              restbedarf_kwh: capacity * (1 - soc / 100), fenster_start_ts: now - 3600, simulation_ende_ts: now + 18000,
              grund: 'Ladefreigabe bleibt bestehen; AstraMeter regelt den Überschuss', fehlmenge_bevorzugt_kwh: 0.8 },
            [`ladefreigabe_venus_${s}_ursprung`]: { zeit_ts: now - 3600, grund: 'Schwacher Tag: früh laden, keine Mittagsspitzenkappung', soc_profil: 'schwach', soc_ziel: 50 },
            [`restzeit_venus_${s}`]: { modus: power < 0 ? 'laden' : 'pausiert', restzeit_s: power < 0 ? 8669 : null, ziel_soc: 100, ziel_ts: now + 8669, leistung_geglaettet_w: 547 } });
          src(`soc_${s}`, soc, '%'); src(`power_${s}`, power, 'W'); src(`charge_limit_${s}`, 1300, 'W');
          src(`discharge_limit_${s}`, letter === 'A' ? 1500 : 2500, 'W'); src(`min_soc_${s}`, 12, '%'); src(`max_soc_${s}`, 100, '%');
          src(`cell_voltage_${s}`, 3.34, 'V'); src(`cell_temp_min_${s}`, 24, '°C'); src(`cell_temp_max_${s}`, 25, '°C'); src(`drift_${s}`, 3, 'mV');
          if (letter === 'A') { src('pack_soc_a1', 55, '%'); src('pack_soc_a2', 56, '%'); sources.pack_soc_a = [sources.pack_soc_a1, sources.pack_soc_a2]; }
          set(`daten_venus_${s}`, 'bereit'); set(`wirkungsgrad_venus_${s}`, power < 0 ? 89 : 'unknown'); set(`verlustleistung_venus_${s}`, power < 0 ? 60 : 'unknown');
          for (const [name, val] of [['bevorzugte_ladeleistung', preferred], ['maximale_ladeleistung', letter === 'A' ? 1500 : 2500], ['maximale_entladeleistung', letter === 'A' ? 1500 : 2500]]) set(`${name}_venus_${s}`, val, { min: 0, max: 2500, step: 50, unit_of_measurement: 'W' }, 'number');
          for (const [cls, value] of [['schwach', 50], ['wechselhaft', 40], ['mittel', 30], ['stark', 0]]) set(`fruehes_ladeziel_venus_${s}_${cls}`, value, { min: 0, max: 100, step: 1, unit_of_measurement: '%' }, 'number');
          for (const day of ['heute', 'morgen']) cal[`${day}_${s}`] = { ok: true, start: now + 600, end: now + 27000, longest_h: 9.4, required_h: 7.2, energy_kwh: 3.77, energy_source: 'Modellreferenz' };
        }
        src('pv', 2296, 'W'); src('grid', -36, 'W'); src('house', 1705, 'W');
        set('status', 'Bereit', { betriebsart: 'Automatik', schreibzugriffe_aktiv: true, planung_aktiv: true, quellen_verfuegbar: 43, quellen_gesamt: 43, warnungen: [], fehlende_entitaeten: [] });
        set('planung', 'Ladefreigabe aktiv', plan); set('kalibrierung', 'Bereit', cal); set('betriebsart', 'Automatik'); set('daten_gemeinsam', 'bereit');
        for (const [key, val, unit] of [['kalibrierleistung', 500, 'W'], ['kalibrierung_ruhe_unten', 45, 'min'], ['kalibrierung_ruhe_oben', 90, 'min'], ['mittag_vorlauf', 1.5, 'h'], ['mittag_nachlauf', 2, 'h'], ['unplanbare_reserve', 1, 'kWh'], ['prognose_sicherheit', 90, '%'], ['ladewirkungsgrad', 90, '%'], ['planung_hysterese', 0.2, 'kWh'], ['knappheitsreserve', 125, '%'], ['schwacher_tag', 20, 'kWh'], ['mittlerer_tag', 50, 'kWh'], ['starker_tag', 85, 'kWh']]) set(key, val, { min: 0, max: 2500, step: 0.1, unit_of_measurement: unit }, 'number');
        window.serviceCalls = [];
        p._panel = { config: { version: '2.2.0 · Vorschau', models: ['A', 'E'], entities, sources } };
        p._hass = { states, themes: { darkMode: true }, callService: (...args) => { window.serviceCalls.push(args); return Promise.resolve(); } };
        document.body.append(p); window.panel = p;
      }, tag);
    }
    await mount();
    async function noOverflow(label) {
      const widths = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth,
        cards: [...window.panel.shadowRoot.querySelectorAll('.card')].filter(el => el.scrollWidth > el.clientWidth + 2).map(el => el.className) }));
      assert.ok(widths.page <= widths.viewport + 2, `${label}: page overflow ${JSON.stringify(widths)}`);
      assert.deepEqual(widths.cards, [], `${label}: card overflow`);
    }
    await page.locator('[data-appearance-toggle]').click();
    await page.locator('[data-appearance="theme"]').selectOption('light');
    await page.locator('[data-appearance="accent"]').selectOption('violet');
    await page.locator('[data-appearance="batteryE"]').selectOption('blue');
    await page.locator('[data-appearance="density"]').selectOption('compact');
    await page.locator('[data-appearance="motion"]').selectOption('off');
    await noOverflow('appearance mobile');
    await page.screenshot({ path: path.join(out, 'mobile-appearance.png'), fullPage: true });
    assert.equal(await page.locator('.flow-dots.active').first().evaluate(el => getComputedStyle(el).display), 'none');
    assert.deepEqual(await page.evaluate(() => window.serviceCalls), []);
    await mount();
    assert.equal(await page.locator(tag).getAttribute('data-theme'), 'light');
    assert.equal(await page.locator(tag).getAttribute('data-density'), 'compact');
    assert.equal(await page.locator(tag).evaluate(el => el.style.getPropertyValue('--accent')), '#7542ba');
    for (const [width, theme, density] of [[390, 'light', 'compact'], [1280, 'dark', 'comfortable']]) {
      await page.setViewportSize({ width, height: 900 });
      await page.evaluate(([theme, density]) => { window.panel._setAppearance('theme', theme); window.panel._setAppearance('density', density); }, [theme, density]);
      for (const tab of ['overview', 'batteries', 'calibration', 'control', 'diagnostics']) {
        await page.locator(`[data-tab="${tab}"]`).click();
        await noOverflow(`${width} ${tab}`);
        await page.screenshot({ path: path.join(out, `${width}-${theme}-${tab}.png`), fullPage: true });
      }
    }
    // Open details survive live updates and switching tabs.
    await page.locator('[data-tab="batteries"]').click();
    await page.locator('[data-remember-details="battery-a"] summary').click();
    await page.evaluate(() => window.panel._render());
    assert.equal(await page.locator('[data-remember-details="battery-a"]').getAttribute('open'), '');
    await page.locator('[data-tab="overview"]').click();
    await page.locator('[data-tab="batteries"]').click();
    assert.equal(await page.locator('[data-remember-details="battery-a"]').getAttribute('open'), '');
    // Calibration controls still target their original HA services.
    await page.evaluate(() => { window.panel._panel.config.entities.kalibrierung_venus_e_morgen = 'button.fixture_calibrate_e'; });
    await page.locator('[data-tab="calibration"]').click();
    await page.locator('[data-press="kalibrierung_venus_e_morgen"]').click();
    assert.deepEqual(await page.evaluate(() => window.serviceCalls), [['button', 'press', { entity_id: 'button.fixture_calibrate_e' }]]);
    await page.locator('[data-tab="control"]').click();
    assert.equal(await page.locator('.calibration-card').count(), 0);
    await page.locator('[data-appearance-toggle]').click();
    await page.locator('[data-appearance="theme"]').selectOption('auto');
    await page.evaluate(() => { window.panel.hass = { ...window.panel.hass, themes: { darkMode: false } }; });
    assert.equal(await page.locator(tag).getAttribute('data-theme'), 'light');
    await page.locator('[data-appearance="motion"]').selectOption('normal');
    await page.locator('[data-appearance-close]').click();
    await page.locator('[data-tab="overview"]').click();
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.locator('.flow-dots.active').first().evaluate(el => getComputedStyle(el).animationName), 'none');
    // All navigation remains reachable on a very narrow screen.
    await page.setViewportSize({ width: 320, height: 740 });
    for (const tab of ['overview', 'batteries', 'calibration', 'control', 'diagnostics']) {
      await page.locator(`[data-tab="${tab}"]`).click();
      await noOverflow(`320 ${tab}`);
    }
    assert.deepEqual(errors, []);
    console.log('Browser checks passed: theme, persistence, no device writes, all five tabs at 320/390/1280px, details, calibration actions, reduced motion.');
  } finally { await browser.close(); }
})().catch(err => { console.error(err); process.exit(1); });
