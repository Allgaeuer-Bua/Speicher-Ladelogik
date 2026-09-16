/* Speicher-Ladelogik — self-contained Home Assistant sidebar dashboard. */

const TABS = [
  ["overview", "mdi:view-dashboard-outline", "Übersicht"],
  ["batteries", "mdi:battery-high", "Speicher"],
  ["control", "mdi:tune-variant", "Steuerung"],
  ["diagnostics", "mdi:stethoscope", "Diagnose"],
];

const PHASE_LABELS = {
  idle: "Bereit",
  requested: "Auftrag vorgemerkt",
  drain: "Entladen auf 13 %",
  wait: "Warten auf PV-Fenster",
  charge: "Kalibrierladung mit 500 W",
  rest: "Ruheprüfung",
  paused: "Pausiert",
  restore: "Grenzwerte wiederherstellen",
  done: "Erfolgreich beendet",
  incomplete: "Wiederholung vorgemerkt",
  cancelled: "Abgebrochen",
  error: "Fehler",
};

const NUMBER_GROUPS = {
  leistung: [
    ["bevorzugte_ladeleistung_venus_a", "Venus A", "Bevorzugte Ladeleistung"],
    ["bevorzugte_ladeleistung_venus_e", "Venus E", "Bevorzugte Ladeleistung"],
    ["min_effiziente_leistung", "Mindestleistung", "Effiziente Untergrenze"],
  ],
  planung: [
    ["mindestreserve", "Mindestreserve", "Garantierte Energiereserve"],
    ["unplanbare_reserve", "Wolkenreserve", "Reserve für unplanbare Erzeugung"],
    ["prognose_sicherheit", "Prognosesicherheit", "Abschlag auf die Vorhersage"],
    ["ladewirkungsgrad", "Planungswirkungsgrad", "AC-Verluste der Ladung"],
    ["planung_hysterese", "Planungshysterese", "Beruhigt kleine Planänderungen"],
    ["knappheitsreserve", "Knappheitsreserve", "Zusätzlicher Puffer an knappen Tagen"],
  ],
  tagesklassen: [
    ["schwacher_tag", "Schwacher Tag", "Grenze der Tagesprognose"],
    ["mittlerer_tag", "Mittlerer Tag", "Grenze der Tagesprognose"],
    ["starker_tag", "Starker Tag", "Grenze der Tagesprognose"],
  ],
};

const esc = (value) => String(value ?? "—")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

class SpeicherLadelogikPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "overview";
    this._hass = null;
    this._panel = null;
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
    this._render();
  }

  get panel() {
    return this._panel;
  }

  connectedCallback() {
    this._render();
  }

  _config() {
    return this._panel?.config || {};
  }

  _eid(key) {
    return this._config().entities?.[key] || null;
  }

  _sid(key) {
    const value = this._config().sources?.[key];
    return typeof value === "string" ? value : null;
  }

  _state(key) {
    const entityId = this._eid(key);
    return entityId ? this._hass?.states?.[entityId] : null;
  }

  _source(key) {
    const entityId = this._sid(key);
    return entityId ? this._hass?.states?.[entityId] : null;
  }

  _attr(key, attribute, fallback = null) {
    const value = this._state(key)?.attributes?.[attribute];
    return value === undefined || value === null ? fallback : value;
  }

  _num(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  _entityNum(entity, fallback = 0) {
    return this._num(entity?.state, fallback);
  }

  _power(value) {
    const watts = this._num(value, NaN);
    if (!Number.isFinite(watts)) return "—";
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toLocaleString("de-DE", { maximumFractionDigits: 2 })} kW`;
    return `${Math.round(watts).toLocaleString("de-DE")} W`;
  }

  _energy(value) {
    const number = this._num(value, NaN);
    if (!Number.isFinite(number)) return "—";
    return `${number.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 2 })} kWh`;
  }

  _percent(value, digits = 0) {
    const number = this._num(value, NaN);
    return Number.isFinite(number)
      ? `${number.toLocaleString("de-DE", { maximumFractionDigits: digits })} %`
      : "—";
  }

  _decimal(value, digits = 2) {
    const number = this._num(value, NaN);
    return Number.isFinite(number)
      ? number.toLocaleString("de-DE", { maximumFractionDigits: digits })
      : "—";
  }

  _measurement(entity, defaultUnit = "", digits = 2) {
    if (!this._available(entity)) return "—";
    const unit = entity.attributes?.unit_of_measurement || defaultUnit;
    return `${this._decimal(entity.state, digits)}${unit ? ` ${unit}` : ""}`;
  }

  _drift(entity) {
    if (!this._available(entity)) return "—";
    const unit = String(entity.attributes?.unit_of_measurement || "mV").toLowerCase();
    const raw = this._num(entity.state, NaN);
    if (!Number.isFinite(raw)) return "—";
    const millivolts = unit === "v" ? raw * 1000 : raw;
    return `${this._decimal(millivolts)} mV`;
  }

  _sourceStates(key) {
    const source = this._config().sources?.[key];
    const entityIds = Array.isArray(source) ? source : source ? [source] : [];
    return entityIds.map((entityId) => this._hass?.states?.[entityId]).filter(Boolean);
  }

  _statusLabel(value) {
    const text = String(value ?? "—");
    const match = text.match(/^Kalibrierung\s+([AE]):\s*([a-z_]+)$/i);
    if (match) return `Kalibrierung ${match[1].toUpperCase()}: ${PHASE_LABELS[match[2].toLowerCase()] || match[2]}`;
    return PHASE_LABELS[text.toLowerCase()] || text;
  }

  _batteryMode(power) {
    if (power < -10) return { label: "Lädt", tone: "charge" };
    if (power > 10) return { label: "Entlädt", tone: "discharge" };
    return { label: "Bereit", tone: "idle" };
  }

  _flowParticle(active, from, to, color) {
    if (!active) return "";
    return `<circle r="5" fill="${color}" class="flow-particle"><animateMotion dur="2.2s" repeatCount="indefinite" path="M ${from} L ${to}" /></circle>`;
  }

  _time(timestamp) {
    const seconds = this._num(timestamp, 0);
    if (!seconds) return "—";
    return new Date(seconds * 1000).toLocaleTimeString("de-DE", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _dateTime(timestamp) {
    const seconds = this._num(timestamp, 0);
    if (!seconds) return "—";
    return new Date(seconds * 1000).toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  _isOn(key) {
    return this._state(key)?.state === "on";
  }

  _available(entity) {
    return Boolean(entity && !["unknown", "unavailable"].includes(entity.state));
  }

  _badge(label, tone = "neutral") {
    return `<span class="badge ${esc(tone)}">${esc(label)}</span>`;
  }

  _cardTitle(icon, title, extra = "") {
    return `<div class="card-title"><span><ha-icon icon="${esc(icon)}"></ha-icon>${esc(title)}</span>${extra}</div>`;
  }

  _header() {
    const version = this._config().version || this._attr("status", "version", "");
    return `
      <header>
        <div class="brand-mark"><ha-icon icon="mdi:battery-charging-medium"></ha-icon></div>
        <div class="brand-copy">
          <strong>Speicher-Ladelogik</strong>
          <span>PV-Fahrplan${version ? ` · ${esc(version)}` : ""}</span>
        </div>
        <nav>
          ${TABS.map(([id, icon, label]) => `
            <button class="nav-item ${this._tab === id ? "active" : ""}" data-tab="${id}">
              <ha-icon icon="${icon}"></ha-icon><span>${label}</span>
            </button>`).join("")}
        </nav>
        <div class="live-pill"><span></span> Live</div>
      </header>`;
  }

  _systemCard() {
    const status = this._state("status");
    const mode = this._attr("status", "betriebsart", this._state("betriebsart")?.state || "—");
    const valid = status?.state === "Bereit";
    const writes = Boolean(this._attr("status", "schreibzugriffe_aktiv", false));
    const socA = this._entityNum(this._source("soc_a"), this._num(this._attr("status", "soc_venus_a", 0)));
    const socE = this._entityNum(this._source("soc_e"), this._num(this._attr("status", "soc_venus_e", 0)));
    const capA = this._entityNum(this._state("nennkapazitaet_venus_a"), 4.16);
    const capE = this._entityNum(this._state("nennkapazitaet_venus_e"), 5.12);
    const combined = Math.max(0, Math.min(100, (socA * capA + socE * capE) / Math.max(0.1, capA + capE)));
    const planStatus = this._statusLabel(this._state("planung")?.state || "—");
    const calibration = this._state("kalibrierung")?.state || "—";
    const peak = this._isOn("mittagsspitzen");
    return `
      <section class="card system-card span-full">
        ${this._cardTitle("mdi:shield-check-outline", "Systemstatus", this._badge(valid ? "Daten bereit" : "Daten prüfen", valid ? "good" : "bad"))}
        <div class="system-grid">
          <div class="soc-ring" style="--soc:${combined.toFixed(1)}">
            <div><strong>${Math.round(combined)}<small>%</small></strong><span>Gesamt</span></div>
          </div>
          <div class="status-table">
            ${this._statusLine("Betriebsart", mode, mode === "Automatik" ? "good" : "warn")}
            ${this._statusLine("Regelung", writes ? "Schreibzugriffe aktiv" : "Beobachten", writes ? "good" : "neutral")}
            ${this._statusLine("Fahrplan", planStatus, "accent")}
            ${this._statusLine("Mittagsspitze", peak ? "Aktiv" : "Aus", peak ? "good" : "neutral")}
            ${this._statusLine("Kalibrierung", calibration, calibration === "Bereit" ? "neutral" : "warn")}
          </div>
        </div>
      </section>`;
  }

  _statusLine(label, value, tone) {
    return `<div class="status-line"><span>${esc(label)}</span>${this._badge(value, tone)}</div>`;
  }

  _flowCard() {
    const pv = this._entityNum(this._source("pv"), this._num(this._attr("status", "pv_ac_w", 0)));
    const grid = this._entityNum(this._source("grid"), NaN);
    const home = this._entityNum(this._source("house"), NaN);
    const powerA = this._entityNum(this._source("power_a"), this._num(this._attr("status", "ac_leistung_venus_a_w", 0)));
    const powerE = this._entityNum(this._source("power_e"), this._num(this._attr("status", "ac_leistung_venus_e_w", 0)));
    const modeA = this._batteryMode(powerA);
    const modeE = this._batteryMode(powerE);
    const gridPath = grid >= 0 ? ["170 90", "500 240"] : ["500 240", "170 90"];
    const aPath = powerA < -10 ? ["500 240", "170 400"] : ["170 400", "500 240"];
    const ePath = powerE < -10 ? ["500 240", "830 400"] : ["830 400", "500 240"];
    return `
      <section class="card flow-card span-7">
        ${this._cardTitle("mdi:transmission-tower", "Energiefluss", this._badge("Live", "good"))}
        <div class="flow-canvas">
          <div class="flow-node grid"><ha-icon icon="mdi:transmission-tower"></ha-icon><strong>${this._power(Math.abs(grid))}</strong><span>${grid > 0 ? "Netzbezug" : "Einspeisung"}</span></div>
          <div class="flow-node pv"><ha-icon icon="mdi:solar-power-variant"></ha-icon><strong>${this._power(pv)}</strong><span>PV</span></div>
          <div class="flow-core"><ha-icon icon="mdi:home-lightning-bolt-outline"></ha-icon><strong>${this._power(home)}</strong><span>Haus</span></div>
          <div class="flow-node batt-a"><ha-icon icon="mdi:battery-charging-60"></ha-icon><strong>${this._power(Math.abs(powerA))}</strong><span>Venus A · ${modeA.label.toLowerCase()}</span></div>
          <div class="flow-node batt-e"><ha-icon icon="mdi:battery-charging-60"></ha-icon><strong>${this._power(Math.abs(powerE))}</strong><span>Venus E · ${modeE.label.toLowerCase()}</span></div>
          <svg class="flow-lines" viewBox="0 0 1000 480" preserveAspectRatio="none" aria-hidden="true">
            <line x1="170" y1="90" x2="500" y2="240"></line>
            <line x1="830" y1="90" x2="500" y2="240"></line>
            <line x1="170" y1="400" x2="500" y2="240"></line>
            <line x1="830" y1="400" x2="500" y2="240"></line>
            ${this._flowParticle(Math.abs(grid) > 10, gridPath[0], gridPath[1], "#ff9a55")}
            ${this._flowParticle(pv > 10, "830 90", "500 240", "#ffbd45")}
            ${this._flowParticle(Math.abs(powerA) > 10, aPath[0], aPath[1], modeA.tone === "charge" ? "#38d582" : "#b493ff")}
            ${this._flowParticle(Math.abs(powerE) > 10, ePath[0], ePath[1], modeE.tone === "charge" ? "#38d582" : "#b493ff")}
          </svg>
        </div>
      </section>`;
  }

  _planningCard() {
    const state = this._state("planung");
    const stateLabel = this._statusLabel(state?.state || "—");
    const reason = this._attr("planung", "entscheidungsgrund", this._attr("planung", "normaler_fahrplan_grund", "Keine Begründung verfügbar"));
    const progress = Math.max(0, Math.min(100, this._num(this._attr("planung", "fenster_fortschritt_prozent", 0))));
    const lockedUntil = this._attr("planung", "fahrplan_entscheidung_fixiert_bis_ts");
    return `
      <section class="card plan-card span-5 entity-card" data-entity="${esc(this._eid("planung"))}">
        ${this._cardTitle("mdi:timeline-clock-outline", "Tagesplanung", this._badge(stateLabel, "accent"))}
        <div class="decision"><strong>${esc(this._attr("planung", "normaler_fahrplan_status", state?.state || "—"))}</strong><p>${esc(reason)}</p></div>
        <div class="metric-pairs">
          ${this._metric("Prognose heute", this._energy(this._attr("planung", "prognose_heute_erwartet_kwh")), "mdi:weather-sunny")}
          ${this._metric("Prognose morgen", this._energy(this._attr("planung", "prognose_morgen_kwh")), "mdi:weather-sunset-up")}
          ${this._metric("Restbedarf", this._energy(this._attr("planung", "restbedarf_kwh")), "mdi:battery-arrow-up")}
          ${this._metric("Sollleistung", this._power(this._attr("planung", "soll_ladeleistung_gesamt_w")), "mdi:flash")}
        </div>
        <div class="window-label"><span>Ladefenster</span><small>Zeitraum für die geplante PV-Ladung</small></div>
        <div class="window-row"><span>${this._time(this._attr("planung", "ladefenster_start_ts"))}</span><div class="progress"><i style="width:${progress}%"></i></div><span>${this._time(this._attr("planung", "ladefenster_ende_ts"))}</span></div>
        <div class="slot-note"><ha-icon icon="mdi:lock-clock"></ha-icon> Entscheidung fixiert bis ${this._time(lockedUntil)}</div>
      </section>`;
  }

  _metric(label, value, icon) {
    return `<div class="metric"><ha-icon icon="${icon}"></ha-icon><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
  }

  _batteryCard(letter, full = false) {
    const suffix = letter.toLowerCase();
    const soc = this._entityNum(this._source(`soc_${suffix}`), this._num(this._attr("status", `soc_venus_${suffix}`, 0)));
    const power = this._entityNum(this._source(`power_${suffix}`), this._num(this._attr("status", `ac_leistung_venus_${suffix}_w`, 0)));
    const minSoc = this._entityNum(this._source(`min_soc_${suffix}`), this._num(this._attr("planung", `untere_geraetegrenze_venus_${suffix}_prozent`, 0)));
    const maxSoc = this._entityNum(this._source(`max_soc_${suffix}`), this._num(this._attr("planung", `obere_geraetegrenze_venus_${suffix}_prozent`, 100)));
    const target = this._num(this._attr("planung", `soll_ladegrenze_venus_${suffix}_w`, 0));
    const valid = this._state(`daten_venus_${suffix}`)?.state === "bereit";
    const efficiency = this._state(`wirkungsgrad_venus_${suffix}`)?.state;
    const loss = this._state(`verlustleistung_venus_${suffix}`)?.state;
    const mode = this._batteryMode(power);
    return `
      <section class="card battery-card ${full ? "battery-full" : ""}">
        ${this._cardTitle("mdi:battery-high", `Venus ${letter}`, this._badge(valid ? "Daten bereit" : "Daten fehlen", valid ? "good" : "bad"))}
        <div class="battery-main">
          <div class="battery-gauge"><div style="height:${Math.max(4, Math.min(100, soc))}%"></div><span>${Math.round(soc)}%</span></div>
          <div class="battery-now"><span class="mode-dot ${mode.tone}"></span><strong>${mode.label}</strong><b>${this._power(Math.abs(power))}</b><small>Sollgrenze ${this._power(target)}</small></div>
        </div>
        <div class="soc-scale"><span>Min ${this._percent(minSoc)}</span><i><b style="left:${Math.max(0, Math.min(100, soc))}%"></b></i><span>Max ${this._percent(maxSoc)}</span></div>
        <div class="metric-pairs compact">
          ${this._metric("Restbedarf", this._energy(this._attr("planung", `restbedarf_venus_${suffix}_kwh`)), "mdi:battery-arrow-up")}
          ${this._metric("Wirkungsgrad", this._percent(efficiency, 1), "mdi:percent-outline")}
          ${this._metric("Verlust", this._power(loss), "mdi:lightning-bolt-outline")}
          ${this._metric("Register", this._power(this._attr("planung", `fahrplan_ladegrenze_stabil_venus_${suffix}_w`)), "mdi:knob")}
        </div>
        ${full ? this._batteryDetails(letter) : ""}
      </section>`;
  }

  _batteryDetails(letter) {
    const s = letter.toLowerCase();
    const packStates = this._sourceStates(`pack_soc_${s}`);
    if (!packStates.length && s === "e" && this._source("soc_e")) packStates.push(this._source("soc_e"));
    const driftStates = this._sourceStates(`drift_${s}`);
    const packs = packStates.map((entity) => this._measurement(entity, "%"));
    const drifts = driftStates.map((entity) => this._drift(entity));
    const voltage = this._measurement(this._source(`cell_voltage_${s}`), "V");
    const maxTemp = this._measurement(this._source(`cell_temp_max_${s}`), "°C");
    const minTemp = this._measurement(this._source(`cell_temp_min_${s}`), "°C");
    const latch = Boolean(this._attr("planung", `ziel_venus_${s}_latch_aktiv`, false));
    return `
      <div class="detail-grid">
        ${this._detail("Pack-SoC", packs.length ? packs.join(" / ") : "—")}
        ${this._detail("Zellspannung max.", voltage)}
        ${this._detail("Zelltemperatur", maxTemp !== "—" ? `${minTemp}–${maxTemp}` : "—")}
        ${this._detail("Zelldrift", drifts.length ? drifts.join(" / ") : "—")}
        ${this._detail("Zielstatus", latch ? "Geräteziel erreicht" : "Ladebedarf vorhanden")}
        ${this._detail("Messwert", this._attr("planung", `ac_leistung_venus_${s}_status`, "—"))}
      </div>`;
  }

  _detail(label, value) {
    return `<div class="detail"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;
  }

  _peakCard() {
    const active = this._isOn("mittagsspitzen");
    const planable = Boolean(this._attr("planung", "mittagsspitzen_planbar", false));
    return `
      <section class="card peak-card span-full entity-card" data-entity="${esc(this._eid("mittagsspitzen"))}">
        ${this._cardTitle("mdi:chart-bell-curve", "Mittagsspitzenkappung", this._badge(active ? "Aktiv" : "Aus", active ? "good" : "neutral"))}
        <div class="peak-layout">
          ${this._metric("Einspeiseziel", this._power(this._attr("planung", "einspeiseziel_w")), "mdi:transmission-tower-export")}
          ${this._metric("Spitzenfenster", `${this._time(this._attr("planung", "spitzenfenster_start_ts"))}–${this._time(this._attr("planung", "spitzenfenster_ende_ts"))}`, "mdi:clock-outline")}
          ${this._metric("Speicher voll", this._time(this._attr("planung", "spitzenplan_voll_ts")), "mdi:battery-check-outline")}
          ${this._metric("Planbar", planable ? "Ja" : "Derzeit nein", planable ? "mdi:check-circle-outline" : "mdi:information-outline")}
        </div>
      </section>`;
  }

  _overview() {
    return `<main class="grid overview">${this._systemCard()}${this._flowCard()}${this._planningCard()}<div class="battery-pair span-full">${this._batteryCard("A")}${this._batteryCard("E")}</div>${this._peakCard()}</main>`;
  }

  _batteries() {
    return `
      <main class="grid batteries-view">
        <div class="battery-pair span-full">${this._batteryCard("A", true)}${this._batteryCard("E", true)}</div>
        <section class="card span-full">
          ${this._cardTitle("mdi:compare-horizontal", "Unabhängige Fahrplanfreigabe")}
          <div class="comparison-grid">
            ${this._comparison("A", "a")}${this._comparison("E", "e")}
          </div>
        </section>
      </main>`;
  }

  _comparison(letter, suffix) {
    const active = Boolean(this._attr("planung", `fahrplan_slot_aktiv_venus_${suffix}`, false));
    const reason = this._attr("planung", `fahrplan_slot_grund_venus_${suffix}`, "—");
    return `<div class="comparison"><div><strong>Venus ${letter}</strong>${this._badge(active ? "Ladeslot" : "Pausenslot", active ? "good" : "neutral")}</div><p>${esc(reason)}</p></div>`;
  }

  _modeControl() {
    const current = this._state("betriebsart")?.state || this._attr("status", "betriebsart", "Beobachten");
    return `
      <section class="card span-full">
        ${this._cardTitle("mdi:tune-variant", "Betriebsart", this._badge(current, current === "Automatik" ? "good" : "warn"))}
        <div class="mode-select">
          ${["Aus", "Beobachten", "Automatik"].map((mode) => `<button data-mode="${mode}" class="${current === mode ? "active" : ""}"><ha-icon icon="${mode === "Aus" ? "mdi:power" : mode === "Beobachten" ? "mdi:eye-outline" : "mdi:auto-mode"}"></ha-icon><strong>${mode}</strong><span>${mode === "Aus" ? "keine Planung" : mode === "Beobachten" ? "Plan prüfen" : "Register steuern"}</span></button>`).join("")}
        </div>
      </section>`;
  }

  _toggleRow(key, title, description, icon) {
    const on = this._isOn(key);
    return `<div class="control-row entity-card" data-entity="${esc(this._eid(key))}"><ha-icon icon="${icon}"></ha-icon><div><strong>${esc(title)}</strong><span>${esc(description)}</span></div><button class="toggle ${on ? "on" : ""}" data-switch="${esc(key)}" aria-label="${esc(title)}"><i></i></button></div>`;
  }

  _numberRow([key, title, description]) {
    const entity = this._state(key);
    if (!entity) return "";
    const unit = entity.attributes?.unit_of_measurement || "";
    return `<label class="number-row"><ha-icon icon="${unit === "W" ? "mdi:flash" : unit === "%" ? "mdi:percent-outline" : "mdi:tune"}"></ha-icon><div><strong>${esc(title)}</strong><span>${esc(description)}</span></div><div class="number-input"><input type="number" data-number="${esc(key)}" value="${esc(entity.state)}" min="${esc(entity.attributes?.min)}" max="${esc(entity.attributes?.max)}" step="${esc(entity.attributes?.step)}"><span>${esc(unit)}</span></div></label>`;
  }

  _numberCard(title, icon, group) {
    return `<section class="card control-card">${this._cardTitle(icon, title)}<div class="control-list">${NUMBER_GROUPS[group].map((item) => this._numberRow(item)).join("")}</div></section>`;
  }

  _manualCard(letter) {
    const s = letter.toLowerCase();
    return `<section class="card control-card">${this._cardTitle("mdi:hand-back-right-outline", `Handbetrieb Venus ${letter}`, this._badge(this._isOn(`handbetrieb_venus_${s}`) ? "Aktiv" : "Automatik", this._isOn(`handbetrieb_venus_${s}`) ? "warn" : "good"))}<div class="control-list">${this._toggleRow(`handbetrieb_venus_${s}`, "Handbetrieb", "Dauerhafte manuelle Registerwerte", "mdi:hand-back-right-outline")}${this._numberRow([`manuell_laden_venus_${s}`, "Ladeleistung", "Manuelle Ladegrenze"])}${this._numberRow([`manuell_entladen_venus_${s}`, "Entladeleistung", "Manuelle Entladegrenze"])}</div></section>`;
  }

  _actionButton(key, icon, label, tone = "") {
    return `<button class="action-btn ${tone}" data-press="${esc(key)}"><ha-icon icon="${icon}"></ha-icon>${esc(label)}</button>`;
  }

  _calibrationCard() {
    const cal = this._state("kalibrierung");
    const battery = this._attr("kalibrierung", "batterie", "—");
    const reason = this._attr("kalibrierung", "grund", "Kein Auftrag aktiv");
    return `
      <section class="card span-full calibration-card">
        ${this._cardTitle("mdi:battery-sync-outline", "Kalibrierung", this._badge(cal?.state || "—", cal?.state === "Bereit" ? "good" : "warn"))}
        <div class="cal-state"><div><span>Speicher</span><strong>${esc(battery)}</strong></div><div><span>Status</span><strong>${esc(reason)}</strong></div><div><span>Energie</span><strong>${this._energy(this._attr("kalibrierung", "energie_ac_kwh"))}</strong></div></div>
        <div class="action-groups">
          <div><strong>Venus A</strong>${this._actionButton("kalibrierung_venus_a_anfordern", "mdi:play", "Heute")}${this._actionButton("kalibrierung_venus_a_morgen", "mdi:calendar-arrow-right", "Morgen")}${this._actionButton("kalibrierung_venus_a_entfernen", "mdi:playlist-remove", "Vormerkung löschen", "subtle")}</div>
          <div><strong>Venus E</strong>${this._actionButton("kalibrierung_venus_e_anfordern", "mdi:play", "Heute")}${this._actionButton("kalibrierung_venus_e_morgen", "mdi:calendar-arrow-right", "Morgen")}${this._actionButton("kalibrierung_venus_e_entfernen", "mdi:playlist-remove", "Vormerkung löschen", "subtle")}</div>
        </div>
        <div class="danger-actions">${this._actionButton("kalibrierung_abbrechen", "mdi:cancel", "Laufende Kalibrierung abbrechen", "danger")}</div>
      </section>`;
  }

  _control() {
    return `<main class="grid control-view">${this._modeControl()}<section class="card span-full">${this._cardTitle("mdi:chart-bell-curve", "Fahrplanfunktionen")}${this._toggleRow("mittagsspitzen", "Mittagsspitzen reduzieren", "Speicherkapazität für die PV-Spitze freihalten", "mdi:chart-bell-curve")}</section><div class="control-columns span-full">${this._numberCard("Ladeleistungen", "mdi:battery-charging", "leistung")}${this._numberCard("Planungsreserven", "mdi:shield-sun-outline", "planung")}${this._numberCard("Tagesklassen", "mdi:weather-partly-cloudy", "tagesklassen")}</div><div class="control-columns two span-full">${this._manualCard("A")}${this._manualCard("E")}</div>${this._calibrationCard()}</main>`;
  }

  _formatWriteResult(item) {
    if (typeof item === "string") return item;
    if (!item || typeof item !== "object") return String(item ?? "—");
    const battery = item.battery ? `Venus ${item.battery}` : "Register";
    const entityId = String(item.entity || "");
    const register = entityId.includes("entlade")
      ? "Entladeleistung"
      : entityId.includes("lade") ? "Ladeleistung" : entityId.split(".").pop() || "Stellgröße";
    const target = this._power(item.value);
    if (item.ok && item.written) return `${battery}: ${register} auf ${target} gesetzt und bestätigt`;
    if (item.ok) return `${battery}: ${register} stand bereits auf ${target}; kein Schreiben erforderlich`;
    return `${battery}: ${register} auf ${target} fehlgeschlagen${item.error ? ` – ${item.error}` : ""}`;
  }

  _diagnostics() {
    const status = this._state("status");
    const warnings = this._attr("status", "warnungen", []) || [];
    const missing = this._attr("status", "fehlende_entitaeten", []) || [];
    const results = (this._attr("status", "letzte_schreibergebnisse", []) || []).map((item) => this._formatWriteResult(item));
    const dataErrors = this._attr("planung", "datenfehler_aktuell", []) || [];
    const comparison = this._state("planvergleich");
    return `
      <main class="grid diagnostics-view">
        <section class="card span-6">${this._cardTitle("mdi:database-check-outline", "Datenquellen")}${this._diagLine("Gemeinsame Daten", this._state("daten_gemeinsam")?.state)}${this._diagLine("Venus A", this._state("daten_venus_a")?.state)}${this._diagLine("Venus E", this._state("daten_venus_e")?.state)}${this._diagLine("Verfügbare Quellen", `${this._attr("status", "quellen_verfuegbar", 0)} / ${this._attr("status", "quellen_gesamt", 0)}`)}</section>
        <section class="card span-6">${this._cardTitle("mdi:file-compare-outline", "Planvergleich", this._badge(comparison?.state || "—", comparison?.state === "Übereinstimmend" ? "good" : "warn"))}${this._diagLine("Schattenplanung", this._attr("status", "schattenplanung_aktiv", false) ? "Aktiv" : "Aus")}${this._diagLine("Letzter Schreibzugriff", this._dateTime(this._attr("status", "letzter_schreibzugriff_ts")))}${this._diagLine("Letzter Schreibfehler", this._attr("status", "letzter_schreibfehler", "Keiner"))}</section>
        ${this._listCard("Aktuelle Hinweise", "mdi:alert-circle-outline", [...warnings, ...dataErrors], "Keine aktuellen Warnungen", "span-6")}
        ${this._listCard("Fehlende Entitäten", "mdi:database-remove-outline", missing, "Keine Entität fehlt", "span-6")}
        ${this._listCard("Letzte Schreibergebnisse", "mdi:pencil-outline", results, "Noch keine Schreibzugriffe", "span-full")}
        <section class="card span-full ack-card">${this._cardTitle("mdi:shield-lock-open-outline", "Schreibsperren und Quittierung")}<p>Die Quittierung setzt die internen Schreibfehlerzähler von Venus A und Venus E zurück. Fehlende oder ungültige Sensorwerte werden dadurch nicht verändert.</p><div class="ack-state">${this._diagLine("Schreibzugriffe", this._attr("status", "schreibzugriffe_aktiv", false) ? "Aktiv" : "Gesperrt")}${this._diagLine("Letzter Schreibfehler", this._attr("status", "letzter_schreibfehler", "Keiner"))}</div><div class="ack-row">${this._actionButton("fehler_quittieren", "mdi:check-decagram-outline", "Schreibfehler quittieren")}</div></section>
      </main>`;
  }

  _diagLine(label, value) {
    const ready = ["bereit", "Bereit", "Keiner", "Aktiv"].includes(String(value));
    return `<div class="diag-line"><span>${esc(label)}</span><strong class="${ready ? "ok" : ""}">${esc(value ?? "—")}</strong></div>`;
  }

  _listCard(title, icon, items, empty, width) {
    return `<section class="card ${width}">${this._cardTitle(icon, title)}<div class="message-list">${items.length ? items.map((item) => `<div><ha-icon icon="mdi:chevron-right"></ha-icon>${esc(typeof item === "string" ? item : JSON.stringify(item))}</div>`).join("") : `<p class="empty"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${esc(empty)}</p>`}</div></section>`;
  }

  _styles() {
    return `
      :host{display:block;min-height:100%;background:var(--primary-background-color,#0b1013);color:var(--primary-text-color,#edf5f1);font-family:var(--ha-font-family,Roboto,sans-serif);--accent:#38d582;--accent2:#52b8ff;--warn:#ffbd45;--bad:#ff6b6b;--card:var(--ha-card-background,var(--card-background-color,#12191d));--line:rgba(127,155,145,.17);--muted:var(--secondary-text-color,#8faaa0)}*{box-sizing:border-box}button,input{font:inherit}header{min-height:70px;display:flex;align-items:center;padding:10px 22px;gap:12px;background:var(--app-header-background-color,#0d1316);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}.brand-mark{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#69ec9f,#25b96e);color:#06120b}.brand-mark ha-icon{--mdc-icon-size:24px}.brand-copy{display:flex;flex-direction:column;min-width:190px}.brand-copy strong{font-size:16px}.brand-copy span{font-size:11px;color:var(--muted);margin-top:2px}nav{display:flex;align-self:stretch;margin-left:18px}.nav-item{border:0;border-bottom:2px solid transparent;background:transparent;color:var(--muted);padding:0 18px;display:flex;align-items:center;gap:8px;cursor:pointer}.nav-item ha-icon{--mdc-icon-size:19px}.nav-item:hover{color:var(--primary-text-color)}.nav-item.active{color:var(--accent);border-color:var(--accent)}.live-pill{margin-left:auto;padding:5px 9px;border-radius:12px;border:1px solid rgba(56,213,130,.3);font-size:11px;color:var(--accent)}.live-pill span{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 10px var(--accent);margin-right:5px}.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;padding:14px;max-width:1800px;margin:0 auto}.span-full{grid-column:1/-1}.span-7{grid-column:span 7}.span-6{grid-column:span 6}.span-5{grid-column:span 5}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:0 10px 28px rgba(0,0,0,.08);min-width:0}.card-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px;text-transform:uppercase;letter-spacing:.075em;color:var(--muted);font-size:10px;font-weight:700}.card-title>span{display:flex;align-items:center;gap:7px}.card-title ha-icon{--mdc-icon-size:15px}.badge{display:inline-flex;align-items:center;padding:4px 8px;border-radius:20px;background:rgba(130,150,145,.14);color:var(--muted);font-size:10px;text-transform:none;letter-spacing:0;white-space:nowrap}.badge.good{color:#61e69a;background:rgba(56,213,130,.13);border:1px solid rgba(56,213,130,.18)}.badge.bad{color:#ff8a8a;background:rgba(255,107,107,.12)}.badge.warn{color:#ffd078;background:rgba(255,189,69,.12)}.badge.accent{color:#81ccff;background:rgba(82,184,255,.12)}.system-grid{display:grid;grid-template-columns:190px 1fr;gap:28px;align-items:center}.soc-ring{--p:calc(var(--soc)*1%);width:152px;height:152px;border-radius:50%;display:grid;place-items:center;margin:auto;background:conic-gradient(var(--accent) var(--p),rgba(100,130,120,.15) 0);filter:drop-shadow(0 0 13px rgba(56,213,130,.22));position:relative}.soc-ring:before{content:"";position:absolute;inset:10px;border-radius:50%;background:var(--card);box-shadow:inset 0 0 28px rgba(56,213,130,.08)}.soc-ring>div{position:relative;text-align:center;display:flex;flex-direction:column}.soc-ring strong{font-size:36px;line-height:1}.soc-ring small{font-size:16px}.soc-ring span{color:var(--muted);font-size:10px;margin-top:8px;text-transform:uppercase}.status-table{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 24px}.status-line{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px}.status-line>span{color:var(--muted)}.flow-canvas{min-height:310px;position:relative;display:grid;grid-template-columns:1fr 1.1fr 1fr;grid-template-rows:1fr 1fr;align-items:center;justify-items:center;overflow:hidden}.flow-node,.flow-core{z-index:2;text-align:center;display:flex;flex-direction:column;align-items:center;gap:4px}.flow-node ha-icon{width:46px;height:46px;--mdc-icon-size:24px;border-radius:14px;display:grid;place-items:center;background:rgba(100,130,120,.12);color:var(--muted)}.flow-node strong{font-size:17px}.flow-node span,.flow-core span{font-size:10px;color:var(--muted)}.flow-node.pv{grid-area:1/2;color:var(--warn)}.flow-node.pv ha-icon{color:var(--warn);background:rgba(255,189,69,.12)}.flow-node.grid{grid-area:1/1;color:#ff9a55}.flow-node.grid ha-icon{color:#ff9a55}.flow-node.batt-a{grid-area:2/1;color:var(--accent)}.flow-node.batt-e{grid-area:2/3;color:var(--accent)}.flow-core{grid-area:1/3}.flow-core ha-icon{width:64px;height:64px;--mdc-icon-size:32px;border-radius:50%;display:grid;place-items:center;background:rgba(82,184,255,.1);color:var(--accent2);border:1px solid rgba(82,184,255,.2)}.flow-core strong{font-size:18px}.line{position:absolute;height:2px;background:linear-gradient(90deg,transparent,var(--accent2),transparent);opacity:.35;transform-origin:left center}.l1{width:34%;left:18%;top:25%}.l2{width:31%;left:52%;top:25%}.l3{width:38%;left:20%;top:63%;transform:rotate(-23deg)}.l4{width:34%;left:53%;top:50%;transform:rotate(35deg)}.line:after{content:"";position:absolute;width:6px;height:6px;background:var(--accent);border-radius:50%;top:-2px;animation:flow 2.4s linear infinite;box-shadow:0 0 8px var(--accent)}@keyframes flow{from{left:0}to{left:100%}}.decision{padding:13px;border-radius:10px;background:rgba(82,184,255,.07);border-left:3px solid var(--accent2);margin-bottom:12px}.decision strong{font-size:15px}.decision p{font-size:11px;line-height:1.45;color:var(--muted);margin:5px 0 0}.metric-pairs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.metric{display:grid;grid-template-columns:22px 1fr;gap:2px 7px;padding:9px;border-radius:9px;background:rgba(110,135,125,.07)}.metric ha-icon{grid-row:1/3;align-self:center;color:var(--muted);--mdc-icon-size:18px}.metric span{font-size:9px;color:var(--muted)}.metric strong{font-size:12px}.window-row{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;margin-top:13px;color:var(--muted);font-size:10px}.progress{height:5px;background:rgba(120,150,140,.15);border-radius:8px;overflow:hidden}.progress i{display:block;height:100%;background:linear-gradient(90deg,var(--accent2),var(--accent));border-radius:8px}.slot-note{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:6px;margin-top:11px}.slot-note ha-icon{--mdc-icon-size:14px}.battery-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.battery-main{display:grid;grid-template-columns:92px 1fr;gap:18px;align-items:center}.battery-gauge{width:66px;height:116px;border:3px solid rgba(115,145,135,.28);border-radius:10px;position:relative;overflow:hidden;margin:auto}.battery-gauge:before{content:"";position:absolute;width:26px;height:6px;background:rgba(115,145,135,.35);left:17px;top:-8px;border-radius:3px}.battery-gauge>div{position:absolute;bottom:0;width:100%;background:linear-gradient(0deg,#23b969,#65e89b);box-shadow:0 0 18px rgba(56,213,130,.35)}.battery-gauge>span{position:absolute;inset:0;display:grid;place-items:center;font-weight:700;text-shadow:0 1px 3px #000}.battery-now{display:grid;grid-template-columns:12px 1fr;gap:4px 6px}.battery-now .mode-dot{width:8px;height:8px;border-radius:50%;align-self:center;background:var(--muted)}.mode-dot.charge{background:var(--accent);box-shadow:0 0 8px var(--accent)}.mode-dot.discharge{background:#b493ff}.battery-now strong{font-size:13px}.battery-now b{grid-column:2;font-size:25px}.battery-now small{grid-column:2;color:var(--muted)}.soc-scale{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;margin:10px 0;font-size:9px;color:var(--muted)}.soc-scale i{height:3px;background:rgba(120,150,140,.18);position:relative}.soc-scale b{position:absolute;width:7px;height:7px;border-radius:50%;background:var(--accent);top:-2px}.compact{margin-top:10px}.detail-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}.detail{padding:10px;background:rgba(110,135,125,.06);border-radius:8px;display:flex;flex-direction:column;gap:4px}.detail span{font-size:9px;color:var(--muted)}.detail strong{font-size:12px}.peak-layout{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.comparison-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.comparison{padding:13px;border-radius:10px;background:rgba(110,135,125,.06)}.comparison>div{display:flex;align-items:center;justify-content:space-between}.comparison p{color:var(--muted);font-size:11px;margin:8px 0 0}.mode-select{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.mode-select button{padding:15px;border-radius:11px;background:rgba(110,135,125,.06);border:1px solid var(--line);color:var(--primary-text-color);display:grid;grid-template-columns:28px 1fr;gap:2px 7px;text-align:left;cursor:pointer}.mode-select button ha-icon{grid-row:1/3;align-self:center;color:var(--muted)}.mode-select button span{font-size:10px;color:var(--muted)}.mode-select button.active{border-color:var(--accent);background:rgba(56,213,130,.08)}.mode-select button.active ha-icon{color:var(--accent)}.control-columns{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.control-columns.two{grid-template-columns:repeat(2,minmax(0,1fr))}.control-list{display:flex;flex-direction:column}.control-row,.number-row{display:grid;grid-template-columns:28px 1fr auto;gap:9px;align-items:center;padding:11px 0;border-bottom:1px solid var(--line)}.control-row>ha-icon,.number-row>ha-icon{color:var(--muted);--mdc-icon-size:19px}.control-row>div,.number-row>div{display:flex;flex-direction:column}.control-row strong,.number-row strong{font-size:12px}.control-row span,.number-row span{font-size:9px;color:var(--muted);margin-top:3px}.toggle{width:38px;height:21px;border:0;border-radius:15px;background:#46534f;padding:3px;cursor:pointer}.toggle i{display:block;width:15px;height:15px;border-radius:50%;background:#fff;transition:.2s}.toggle.on{background:var(--accent)}.toggle.on i{transform:translateX(17px)}.number-input{flex-direction:row!important;align-items:center;background:rgba(100,130,120,.08);border:1px solid var(--line);border-radius:7px;padding:0 7px}.number-input input{width:74px;border:0;background:transparent;color:var(--primary-text-color);padding:7px 2px;text-align:right;outline:0}.number-input span{margin:0 0 0 4px}.cal-state{display:grid;grid-template-columns:150px 1fr 150px;gap:10px}.cal-state>div{display:flex;flex-direction:column;gap:4px;padding:11px;background:rgba(110,135,125,.06);border-radius:9px}.cal-state span{font-size:9px;color:var(--muted)}.cal-state strong{font-size:12px}.action-groups{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:14px}.action-groups>div{display:flex;gap:8px;align-items:center;padding:12px;border:1px solid var(--line);border-radius:10px}.action-groups>div>strong{margin-right:auto}.action-btn{display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(56,213,130,.28);border-radius:8px;background:rgba(56,213,130,.1);color:var(--primary-text-color);padding:8px 10px;cursor:pointer;font-size:11px}.action-btn:hover{background:rgba(56,213,130,.18)}.action-btn ha-icon{--mdc-icon-size:16px;color:var(--accent)}.action-btn.subtle{border-color:var(--line);background:rgba(110,135,125,.06)}.action-btn.danger{border-color:rgba(255,107,107,.28);background:rgba(255,107,107,.08)}.action-btn.danger ha-icon{color:var(--bad)}.danger-actions{margin-top:12px;text-align:right}.diag-line{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px}.diag-line span{color:var(--muted)}.diag-line strong.ok{color:var(--accent)}.message-list>div{display:flex;gap:5px;padding:8px 0;border-bottom:1px solid var(--line);font-size:11px}.message-list ha-icon{--mdc-icon-size:15px;color:var(--muted)}.empty{display:flex;align-items:center;gap:7px;color:var(--accent);font-size:11px}.entity-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.entity-link{display:flex;flex-direction:column;text-align:left;border:1px solid var(--line);border-radius:8px;background:rgba(110,135,125,.05);color:var(--primary-text-color);padding:8px;cursor:pointer;overflow:hidden}.entity-link span{font-size:9px;color:var(--muted)}.entity-link strong{font-size:10px;white-space:nowrap;text-overflow:ellipsis;overflow:hidden;margin-top:3px}.ack-row{text-align:right;margin-top:12px}.entity-card{cursor:pointer}
      @media(max-width:1050px){.span-7,.span-5{grid-column:1/-1}.control-columns{grid-template-columns:1fr 1fr}.control-columns .control-card:last-child{grid-column:1/-1}.peak-layout{grid-template-columns:repeat(2,1fr)}.action-groups>div{flex-wrap:wrap}.entity-grid{grid-template-columns:repeat(2,1fr)}}
      @media(max-width:720px){header{padding:8px 10px;flex-wrap:wrap}.brand-copy{min-width:0}.brand-copy strong{font-size:14px}.live-pill{display:none}nav{order:3;width:calc(100% + 20px);margin:4px -10px -8px;overflow-x:auto;height:49px}.nav-item{flex:1;min-width:76px;padding:0 8px;justify-content:center}.nav-item span{font-size:10px}.grid{padding:9px;gap:9px}.card{padding:13px;border-radius:11px}.system-grid{grid-template-columns:1fr}.status-table{grid-template-columns:1fr}.soc-ring{width:128px;height:128px}.battery-pair,.control-columns,.control-columns.two,.comparison-grid,.action-groups{grid-template-columns:1fr}.control-columns .control-card:last-child{grid-column:auto}.flow-canvas{min-height:270px}.battery-main{grid-template-columns:76px 1fr}.detail-grid,.entity-grid{grid-template-columns:repeat(2,1fr)}.cal-state{grid-template-columns:1fr}.mode-select{grid-template-columns:1fr}.mode-select button{grid-template-columns:28px 1fr}.peak-layout{grid-template-columns:1fr}.action-groups>div{align-items:stretch}.action-groups>div>strong{width:100%}.metric-pairs{grid-template-columns:1fr 1fr}}
      @media(max-width:410px){.nav-item ha-icon{display:none}.metric-pairs,.detail-grid,.entity-grid{grid-template-columns:1fr}.flow-node strong{font-size:13px}.flow-node span{font-size:8px}.flow-core ha-icon{width:48px;height:48px}.number-row{grid-template-columns:23px 1fr}.number-input{grid-column:2;justify-self:end}}
      :host{background:#0a1013;color:#eaf4ef;--primary-text-color:#eaf4ef;--secondary-text-color:#8da29a;--primary-background-color:#0a1013;--card:#11191d;--muted:#8da29a;--line:rgba(144,177,164,.14)}
      header{background:#0d1418}.card{background:#11191d;box-shadow:0 10px 28px rgba(0,0,0,.22)}
      .flow-canvas{min-height:360px;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr)}
      .flow-node.grid{grid-area:1/1}.flow-node.pv{grid-area:1/3}.flow-core{grid-area:2/2}.flow-node.batt-a{grid-area:3/1}.flow-node.batt-e{grid-area:3/3}
      .flow-lines{position:absolute;inset:0;width:100%;height:100%;z-index:1;overflow:visible}.flow-lines line{stroke:rgba(132,169,156,.25);stroke-width:3;vector-effect:non-scaling-stroke}.flow-particle{filter:drop-shadow(0 0 5px currentColor)}
      .window-label{display:flex;justify-content:space-between;align-items:baseline;margin-top:13px;color:var(--primary-text-color);font-size:10px;font-weight:700}.window-label small{color:var(--muted);font-weight:400}
      .window-row{margin-top:6px}.number-input{width:100px;justify-content:flex-end}.number-input input{width:58px}.ack-card>p{color:var(--muted);font-size:11px;line-height:1.55;margin:0 0 8px}.ack-state{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 24px}
      @media(max-width:720px){.flow-canvas{min-height:320px}.window-label{align-items:flex-start;flex-direction:column;gap:3px}.ack-state{grid-template-columns:1fr}.number-input{width:94px}}
    `;
  }

  _render() {
    if (!this.isConnected || !this._hass || !this._panel) return;
    const content = this._tab === "overview" ? this._overview()
      : this._tab === "batteries" ? this._batteries()
        : this._tab === "control" ? this._control() : this._diagnostics();
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${this._header()}${content}`;
    this._bind();
  }

  _bind() {
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
      this._tab = button.dataset.tab;
      this._render();
    }));
    this.shadowRoot.querySelectorAll("[data-entity]").forEach((element) => element.addEventListener("click", (event) => {
      if (event.target.closest("button,input,select")) return;
      const entityId = element.dataset.entity;
      if (entityId && entityId !== "null") this._moreInfo(entityId);
    }));
    this.shadowRoot.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => this._setMode(button.dataset.mode)));
    this.shadowRoot.querySelectorAll("[data-switch]").forEach((button) => button.addEventListener("click", (event) => {
      event.stopPropagation();
      this._toggle(button.dataset.switch);
    }));
    this.shadowRoot.querySelectorAll("[data-number]").forEach((input) => input.addEventListener("change", () => this._setNumber(input.dataset.number, input.value)));
    this.shadowRoot.querySelectorAll("[data-press]").forEach((button) => button.addEventListener("click", () => this._press(button.dataset.press)));
  }

  _moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  async _setMode(option) {
    const entityId = this._eid("betriebsart");
    if (entityId) await this._hass.callService("select", "select_option", { entity_id: entityId, option });
  }

  async _toggle(key) {
    const entityId = this._eid(key);
    if (!entityId) return;
    await this._hass.callService("switch", this._isOn(key) ? "turn_off" : "turn_on", { entity_id: entityId });
  }

  async _setNumber(key, value) {
    const entityId = this._eid(key);
    const number = Number(value);
    if (entityId && Number.isFinite(number)) await this._hass.callService("number", "set_value", { entity_id: entityId, value: number });
  }

  async _press(key) {
    const entityId = this._eid(key);
    if (!entityId) return;
    const labels = {
      kalibrierung_venus_a_anfordern: "Kalibrierung Venus A heute anfordern?",
      kalibrierung_venus_e_anfordern: "Kalibrierung Venus E heute anfordern?",
      kalibrierung_venus_a_morgen: "Kalibrierung Venus A für morgen vormerken?",
      kalibrierung_venus_e_morgen: "Kalibrierung Venus E für morgen vormerken?",
      kalibrierung_venus_a_entfernen: "Vormerkung für Venus A entfernen?",
      kalibrierung_venus_e_entfernen: "Vormerkung für Venus E entfernen?",
      kalibrierung_abbrechen: "Die laufende Kalibrierung wirklich abbrechen?",
      fehler_quittieren: "Schreibfehler und Sperren quittieren?",
    };
    if (labels[key] && !window.confirm(labels[key])) return;
    await this._hass.callService("button", "press", { entity_id: entityId });
  }
}

if (!customElements.get("speicher-ladelogik-panel")) {
  customElements.define("speicher-ladelogik-panel", SpeicherLadelogikPanel);
}
