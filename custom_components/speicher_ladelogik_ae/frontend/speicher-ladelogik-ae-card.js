/* Speicher-Ladelogik A/E 2.3.1 — native Lovelace views, no sidebar panel. */
import { SpeicherLadelogikPanel, esc } from "./speicher-ladelogik-ae-panel.js?v=2.3.1";
import "./speicher-telemetry.js?v=2.3.1";

const TAG = "speicher-ladelogik-ae-card";
const VIEWS = { overview: "Übersicht", calibration: "Kalibrieren", control: "Steuerung", diagnostics: "Diagnose" };
const finite = value => typeof value === "number" && Number.isFinite(value);

class SpeicherLadelogikCard extends SpeicherLadelogikPanel {
  constructor() {
    super();
    this._manualDrafts = new Map();
    this._manualBusy = new Set();
    this._messages = new Map();
    this._resolveEpoch = 0;
    this._nextResolve = 0;
  }

  setConfig(config = {}) {
    const view = config.view || "overview";
    if (!Object.hasOwn(VIEWS, view)) throw new Error("view: overview, calibration, control oder diagnostics verwenden.");
    if (config.theme && !["light", "dark", "auto"].includes(config.theme)) throw new Error("theme: light, dark oder auto verwenden.");
    this._cardConfig = { ...config, view };
    this._appearance.theme = config.theme || "light";
    this._tab = view;
    this._panel = null;
    this._rendered = false;
    this._manualDrafts.clear();
    this._analytics?.remove();
    this._analytics = null;
    this._analyticsSignature = "";
    this._resolveEpoch++;
    this._resolving = false;
    this._nextResolve = 0;
    this._loadConfig();
    this._render();
  }

  set hass(value) {
    this._hass = value;
    if (!this._cardConfig) return;
    if (!this._panel) this._loadConfig();
    if (this._panel) {
      this._getAnalytics().hass = value;
      this._render();
    }
  }
  get hass() { return this._hass; }

  connectedCallback() {
    if (!this._cardConfig) this.setConfig({});
    super.connectedCallback();
    this._loadConfig();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._valueDialog?.close();
    this._analytics?.remove();
  }

  async _loadConfig() {
    if (!this._hass?.callWS || !this._cardConfig || this._resolving || Date.now() < this._nextResolve) return;
    const epoch = this._resolveEpoch;
    this._resolving = true;
    try {
      const result = await this._hass.callWS({ type: "speicher_ladelogik_ae/config" });
      if (epoch !== this._resolveEpoch) return;
      const entries = result?.entries || [];
      const selected = this._cardConfig.entry_id
        ? entries.find(entry => entry.entry_id === this._cardConfig.entry_id)
        : entries.length === 1 ? entries[0] : null;
      if (!selected) throw new Error(entries.length > 1 ? "Mehrere Integrationen gefunden. entry_id in der Karte angeben." : "Speicher-Ladelogik A/E ist nicht geladen. Integration und Version prüfen.");
      this._panel = { config: selected };
      this._loadError = "";
      this._rendered = false;
      this._getAnalytics().hass = this._hass;
      this._render();
    } catch (error) {
      if (epoch !== this._resolveEpoch) return;
      this._loadError = error.message || "Konfiguration nicht abrufbar. Integration ab Version 2.3.0 installieren.";
      this._nextResolve = Date.now() + 30000;
      this._render();
    } finally {
      if (epoch === this._resolveEpoch) this._resolving = false;
    }
  }

  getCardSize() { return Math.max(4, Math.ceil((this.offsetHeight || 700) / 50)); }
  getGridOptions() { return { columns: "full", min_columns: 6 }; }
  static getStubConfig() { return { type: `custom:${TAG}`, view: "overview", theme: "light" }; }
  _ensureHistory() { /* Read-only telemetry owns lazy, cached Recorder queries. */ }

  _telemetryConfig() {
    const sources = this._config().sources || {};
    const entities = { sign_setting: "" };
    for (const s of ["a", "e"]) {
      for (const [key, source] of [["power", `power_${s}`], ["ac_raw", `power_${s}`], ["soc", `soc_${s}`], ["dc", `dc_${s}`], ["status", `inverter_${s}`], ["charge_limit", `charge_limit_${s}`], ["discharge_limit", `discharge_limit_${s}`]]) {
        entities[`${s}_${key}`] = typeof sources[source] === "string" ? sources[source] : "";
      }
      const drifts = Array.isArray(sources[`drift_${s}`]) ? sources[`drift_${s}`] : [sources[`drift_${s}`]];
      if (s === "a") {
        const packs = sources.pack_soc_a || [];
        for (let i = 1; i <= 2; i++) {
          entities[`a_p${i}_soc`] = packs[i - 1] || "";
          entities[`a_p${i}_drift`] = drifts[i - 1] || "";
        }
      } else {
        entities.e_drift = drifts[0] || "";
        entities.e_cell_max = sources.cell_voltage_e || "";
      }
    }
    return {
      theme: this._effectiveTheme(), enable_controls: false,
      history_hours: this._cardConfig.history_hours || 24,
      history_refresh_seconds: this._cardConfig.history_refresh_seconds || 120,
      history_max_points: this._cardConfig.history_max_points || 720,
      power_deadband_w: this._cardConfig.power_deadband_w ?? 10,
      power_sign: this._cardConfig.power_sign || {},
      grid_power_sign: this._cardConfig.grid_power_sign ?? 1,
      capacity_kwh: this._cardConfig.capacity_kwh || {},
      entities: { ...entities, grid_power: sources.grid || "", ...(this._cardConfig.entities || {}) },
      colors: this._cardConfig.colors || {},
    };
  }

  _getAnalytics() {
    if (!this._analytics) this._analytics = document.createElement("speicher-ladelogik-telemetry");
    const config = this._telemetryConfig();
    const signature = JSON.stringify(config);
    if (this._analyticsSignature !== signature) {
      this._analytics.setConfig(config);
      this._analyticsSignature = signature;
    }
    this._analytics._issues ||= new Set();
    return this._analytics;
  }

  _sourceIds(...keys) {
    return keys.flatMap(key => this._config().sources?.[key] || []).filter(Boolean);
  }

  _telemetryIds(...keys) {
    return keys.map(key => this._getAnalytics()._config.entities[key]).filter(Boolean);
  }

  _valueLink(content, ids, label, className = "") {
    return `<button type="button" class="value-link ${className}" data-value-sources="${esc(JSON.stringify([...new Set(ids.filter(Boolean))]))}" aria-label="${esc(label)} · Entität oder Quellen öffnen">${content}</button>`;
  }

  _metric(label, value, icon, ids = [this._eid("planung")]) {
    return this._valueLink(`<span>${esc(label)}</span><strong>${esc(value)}</strong>`, ids, label, "metric");
  }

  _statusLine(label, value, tone) {
    const key = label === "Kalibrierung" ? "kalibrierung" : label === "Betriebsart" ? "betriebsart" : label === "Regelung" ? "status" : "planung";
    return `<div class="status-line"><span>${esc(label)}</span>${this._valueLink(this._badge(value, tone), [this._eid(key)], label)}</div>`;
  }

  _numberRow(item) {
    const html = super._numberRow(item), id = this._eid(item[0]);
    if (!html || !id) return html;
    return html.replace(`<strong>${esc(item[1])}</strong>`, `<strong>${esc(item[1])}</strong>${this._valueLink("↗", [id], item[1], "setting-source")}`);
  }

  _batteryDetails(slot) {
    this._detailSlot = slot;
    try { return super._batteryDetails(slot); }
    finally { this._detailSlot = null; }
  }

  _detail(label, value) {
    if (!this._detailSlot) return super._detail(label, value);
    const s = this._detailSlot.toLowerCase();
    const ids = label === "Pack-SoC" ? this._sourceIds(`pack_soc_${s}`, ...(s === "e" ? ["soc_e"] : []))
      : label === "Zellspannung max." ? this._sourceIds(`cell_voltage_${s}`)
        : label === "Zelltemperatur" ? this._sourceIds(`cell_temp_min_${s}`, `cell_temp_max_${s}`)
          : label === "Messwert" ? this._sourceIds(`power_${s}`) : [this._eid("planung")];
    return this._valueLink(`<span>${esc(label)}</span><strong>${esc(value)}</strong>`, ids, label, "detail");
  }

  _openValueSources(ids, label) {
    const unique = [...new Set(ids.filter(Boolean))];
    if (unique.length === 1) { this._moreInfo(unique[0]); return; }
    this._valueDialog?.close();
    const dialog = document.createElement("dialog");
    dialog.className = "value-sources";
    dialog.setAttribute("aria-label", label);
    const heading = document.createElement("h3"); heading.textContent = label.replace(/ · Entität oder Quellen öffnen$/, "");
    const note = document.createElement("p");
    note.textContent = unique.length ? "Berechneter oder zusammengesetzter Wert. Quelle zum Öffnen auswählen." : "Dieser Wert stammt aus der Kartenkonfiguration. Kein Sensor zugeordnet.";
    dialog.append(heading, note);
    for (const id of unique) {
      const state = this._hass.states[id], button = document.createElement("button"), name = document.createElement("strong"), identity = document.createElement("small"), value = document.createElement("span");
      button.type = "button"; button.className = "value-source-row";
      name.textContent = state?.attributes?.friendly_name || id; identity.textContent = id;
      value.textContent = state ? `${state.state} ${state.attributes?.unit_of_measurement || ""}`.trim() : "Nicht verfügbar";
      button.append(name, identity, value);
      button.addEventListener("click", () => { dialog.close(); this._moreInfo(id); });
      dialog.append(button);
    }
    const close = document.createElement("button"); close.type = "button"; close.className = "action-btn"; close.textContent = "Schließen";
    close.addEventListener("click", () => dialog.close()); dialog.append(close);
    dialog.addEventListener("close", () => { dialog.remove(); if (this._valueDialog === dialog) this._valueDialog = null; }, { once: true });
    this.shadowRoot.append(dialog); this._valueDialog = dialog; dialog.showModal();
  }

  _telemetryRead(key, kind, unit) {
    const analytics = this._getAnalytics();
    analytics._issues ||= new Set();
    return analytics._read(key, kind, unit);
  }

  _summaryData() {
    const a = this._getAnalytics();
    const values = ["a", "e"].map(s => ({ soc: a._percent(`${s}_soc`), cap: a._capacity(s), power: a._power(s) }));
    const validSoc = values.every(v => finite(v.soc) && finite(v.cap) && v.cap > 0);
    const cap = values.reduce((n, v) => n + v.cap, 0);
    const energy = validSoc ? values.reduce((n, v) => n + v.soc / 100 * v.cap, 0) : NaN;
    const power = values.every(v => finite(v.power)) ? values.reduce((n, v) => n + v.power, 0) : NaN;
    return { energy, cap, power, soc: validSoc ? energy / cap * 100 : NaN };
  }

  _header() {
    const name = this._tab === "overview" ? "Speicher-Ladelogik A/E" : VIEWS[this._tab];
    return `<header class="cockpit-header"><div class="brand-copy"><strong>${esc(name)}</strong><span>Speicher · ${esc(this._config().version || "2.3.1")}</span></div><button class="icon-button appearance-toggle" data-appearance-toggle aria-label="Darstellung anpassen"><ha-icon icon="mdi:palette-outline"></ha-icon></button></header>`;
  }

  _systemCard() {
    const d = this._summaryData();
    const profile = this._attr("planung", "fruehes_soc_ziel_tagesklasse", this._attr("planung", "tagesklasse", "—"));
    const labels = { schwach: "Schwach", wechselhaft: "Wechselhaft", mittel: "Mittel", stark: "Stark" };
    const weighted = this._telemetryIds("a_soc", "e_soc", "a_reference", "e_reference", "reference_ready");
    return `<section class="card system-card span-full">
      ${this._cardTitle("mdi:shield-check-outline", "Systemstatus", this._badge(this._state("status")?.state === "Bereit" ? "Daten bereit" : "Daten prüfen", this._state("status")?.state === "Bereit" ? "good" : "warn"))}
      <div class="summary-grid"><div class="soc-ring" data-live-combined-ring style="--soc:${finite(d.soc) ? d.soc : 0}"><div>${this._valueLink(`<strong><b data-live-combined>${finite(d.soc) ? Math.round(d.soc) : "—"}</b><small>%</small></strong><span>Gesamt</span>`, weighted, "Gesamt-Ladezustand")}</div></div>
      <div class="summary-metric"><span>Gespeicherte Energie</span>${this._valueLink(`<strong data-summary-energy>${finite(d.energy) ? this._energy(d.energy) : "—"}</strong>`, weighted, "Gespeicherte Energie")}${this._valueLink(`<small data-summary-reference>SoC-Schätzung · Referenz ${this._energy(d.cap)}</small>`, this._telemetryIds("a_reference", "e_reference", "reference_ready"), "Referenzkapazität")}</div>
      <div class="summary-metric"><span>Leistung · beide Speicher</span>${this._valueLink(`<strong data-summary-power>${finite(d.power) ? this._power(Math.abs(d.power) * 1000) : "—"}</strong>`, this._telemetryIds("a_power", "e_power", "sign_setting"), "Leistung beider Speicher")}<small data-summary-flow>${!finite(d.power) ? "Daten fehlen" : Math.abs(d.power) <= .01 ? "Bereit" : d.power < 0 ? "Laden" : "Entladen"}</small></div></div>
      <div class="summary-status">${this._statusLine("Tagesklasse heute", labels[profile] || profile, "accent")}${this._statusLine("Planstatus", this._statusLabel(this._state("planung")?.state || "—"), "accent")}</div>
      ${profile === "wechselhaft" ? '<p class="slot-note">Wechselhaft ist das Sicherheitsprofil eines mittleren Tages bei Prognoseunsicherheit.</p>' : ""}
    </section>`;
  }

  _batteryCard(slot) {
    const s = slot.toLowerCase(), a = this._getAnalytics();
    const soc = this._entityNum(this._source(`soc_${s}`), NaN);
    const power = this._entityNum(this._source(`power_${s}`), NaN);
    const electrical = a._electrical(s, a._power(s));
    const cap = a._capacity(s);
    const energy = ["charge", "discharge"].map(k => this._telemetryRead(`${s}_${k}_today`, "energy", "kWh"));
    const limit = key => this._power(this._entityNum(this._source(`${key}_${s}`), NaN));
    return `<article class="battery-card storage-${s}" data-battery="${s}">
      <div class="battery-heading"><h3>${esc(this._storageLabel(slot))}</h3>${this._badge(this._storageStatus(slot).label, this._storageStatus(slot).tone)}</div>
      <div class="battery-current">${this._valueLink(`<strong class="battery-soc" data-live-battery="${s}-soc">${this._percent(soc)}</strong>`, this._sourceIds(`soc_${s}`), `${this._storageLabel(slot)} · SoC`)}<div class="battery-power">${this._valueLink(`<strong data-live-battery="${s}-power">${this._power(Math.abs(power))}</strong>`, this._sourceIds(`power_${s}`), `${this._storageLabel(slot)} · AC-Leistung`)}<span data-live-battery="${s}-mode">${this._batteryMode(power).label}</span></div></div>
      <div class="battery-track"><i data-track="${s}" style="width:${finite(soc) ? soc : 0}%"></i></div><div class="battery-caption">${this._valueLink(`${finite(soc) ? this._energy(soc / 100 * cap) : "—"} · SoC-Schätzung`, this._telemetryIds(`${s}_soc`, `${s}_reference`, "reference_ready"), "Gespeicherte Energie")}${this._valueLink(`Referenz ${this._energy(cap)}`, this._telemetryIds(`${s}_reference`, "reference_ready"), "Referenzkapazität")}</div>
      ${this._valueLink(this._remainingTime(slot), [this._eid("planung")], "Restzeit", "cal-result")}
      <div class="metric-pairs">
        ${this._metric("Restbedarf", this._energy(this._attr("planung", `restbedarf_venus_${s}_kwh`)), "mdi:battery-arrow-up-outline")}
        ${this._metric("Verlustleistung", this._power(electrical.loss), "mdi:flash", this._telemetryIds(`${s}_ac_raw`, `${s}_dc`))}
        ${this._metric("Wirkungsgrad", this._percent(electrical.ratio, 1), "mdi:percent-outline", this._telemetryIds(`${s}_ac_raw`, `${s}_dc`, `${s}_power`))}
        ${this._metric("Ladegrenze", limit("charge_limit"), "mdi:battery-arrow-up-outline", this._sourceIds(`charge_limit_${s}`))}
        ${this._metric("Entladegrenze", limit("discharge_limit"), "mdi:battery-arrow-down-outline", this._sourceIds(`discharge_limit_${s}`))}
        ${this._metric("Heute geladen", this._energy(energy[0]), "mdi:battery-plus-outline", this._telemetryIds(`${s}_charge_today`))}
        ${this._metric("Heute entladen", this._energy(energy[1]), "mdi:battery-minus-outline", this._telemetryIds(`${s}_discharge_today`))}
      </div>
      ${this._batteryDetails(slot)}
      ${this._deviceControls(slot)}
      ${this._electricalDetails(slot, electrical)}
    </article>`;
  }

  _draftFor(slot) {
    if (!this._manualDrafts.has(slot)) {
      const s = slot.toLowerCase();
      const active = this._isOn(`handbetrieb_venus_${s}`);
      this._manualDrafts.set(slot, { active, originalActive: active,
        charge: this._entityNum(active ? this._state(`manuell_laden_venus_${s}`) : this._source(`charge_limit_${s}`), NaN),
        discharge: this._entityNum(active ? this._state(`manuell_entladen_venus_${s}`) : this._source(`discharge_limit_${s}`), NaN),
        mode: this._getAnalytics()._text(`${s}_mode`), dirty: false });
    }
    return this._manualDrafts.get(slot);
  }

  _deviceControls(slot) {
    const s = slot.toLowerCase(), draft = this._draftFor(slot), a = this._getAnalytics();
    const admin = this._hass?.user?.is_admin === true;
    const available = this._available(this._state(`handbetrieb_venus_${s}`));
    const busy = this._manualBusy.has(slot);
    const ranges = ["charge", "discharge"].map((key, index) => {
      const state = this._state(`manuell_${index ? "entladen" : "laden"}_venus_${s}`);
      const physical = this._source(`${key}_limit_${s}`);
      const minimum = Math.max(Number(state?.attributes?.min ?? 0), Number(physical?.attributes?.min ?? 0));
      const maximum = Math.min(Number(state?.attributes?.max ?? NaN), Number(physical?.attributes?.max ?? NaN));
      const step = Number(state?.attributes?.step ?? NaN);
      const ready = this._available(state) && this._available(physical) && [minimum, maximum, step, draft[key]].every(finite) && step > 0 && maximum >= minimum;
      return `<label class="manual-range"><span>${index ? "Maximale Entladeleistung" : "Maximale Ladeleistung"}<output data-output="${key}">${this._power(draft[key])}</output><button type="button" class="source-button" data-info="${esc(this._sid(`${key}_limit_${s}`))}" aria-label="Leistungsentität öffnen">↗</button></span><input type="range" data-manual-range="${key}" min="${minimum}" max="${ready ? maximum : minimum}" step="${finite(step) ? step : 50}" value="${finite(draft[key]) ? draft[key] : minimum}" ${!ready || !admin || busy ? "disabled" : ""}><small>${minimum}–${finite(maximum) ? maximum : "—"} W</small></label>`;
    }).join("");
    const mode = a._state(`${s}_mode`);
    const options = Array.isArray(mode?.attributes?.options) ? mode.attributes.options : [];
    const canMode = this._available(mode) && options.includes(draft.mode);
    return `<details class="device-controls" data-remember-details="control-${s}"><summary>Steuerung</summary><div data-manual-form="${slot}">
      <label class="manual-toggle"><span><strong>Handbetrieb ${esc(this._storageLabel(slot))}</strong><small>Manuelle Lade- und Entladegrenzen statt Automatikplanung für diesen Speicher.</small></span><input type="checkbox" data-manual-active ${draft.active ? "checked" : ""} ${!available || !admin || busy ? "disabled" : ""}></label>
      <label class="device-mode">Betriebsmodus<select data-device-mode ${!canMode || !admin || busy ? "disabled" : ""}>${options.map(option => `<option${option === draft.mode ? " selected" : ""}>${esc(option)}</option>`).join("") || '<option>Keine Geräteoptionen verfügbar</option>'}</select></label>
      ${ranges}
      <div class="manual-apply"><span data-manual-feedback>${esc(!admin ? "Handbetrieb darf nur ein Administrator übernehmen." : this._messages.get(slot) || (draft.dirty ? "Änderungen noch nicht übernommen." : "Automatik bleibt aktiv, bis Handbetrieb mit Übernehmen bestätigt wird."))}</span><button class="action-btn" data-apply-manual ${!admin || !available || !draft.dirty || (!draft.active && !draft.originalActive) || busy ? "disabled" : ""}>${busy ? "Übernehme …" : "Übernehmen"}</button></div>
    </div></details>`;
  }

  _electricalDetails(slot, electrical) {
    const s = slot.toLowerCase(), a = this._getAnalytics();
    const fields = [
      ["AC-Leistung", this._power(finite(electrical.ac) ? Math.abs(electrical.ac) * 1000 : NaN), "ac_raw"],
      ["DC-Leistung", this._power(finite(electrical.dc) ? Math.abs(electrical.dc) * 1000 : NaN), "dc"],
      [electrical.loss < 0 ? "Leistungsdifferenz" : "Verlustleistung · Näherung", this._power(electrical.loss), "dc"],
      [electrical.loss < 0 ? "Rechnerisches Verhältnis" : "Wirkungsgrad · aktuell", this._percent(electrical.ratio, 1), "dc"],
      ...[["DC-Spannung", "voltage", "V", 2], ["DC-Strom", "current", "A", 2], ["Interne Temperatur", "temperature", "°C", 1], ["MOS 1", "mos1", "°C", 1], ["MOS 2", "mos2", "°C", 1], ["Auslastung", "load", "%", 0], ["Nutzbare Kapazität", "usable", "kWh", 2]].map(([name, key, unit, digits]) => [name, this._measurement(a._state(`${s}_${key}`), unit, digits), key]),
      ["Wechselrichter", a._text(`${s}_status`), "status"],
      ["Bis SoC-Minimum", a._duration(`${s}_eta_min`), "eta_min"], ["Bis SoC-Maximum", a._duration(`${s}_eta_max`), "eta_max"],
    ];
    const fan = a._state(`${s}_fan`);
    return `<details class="electrical-details" data-remember-details="electric-${s}"><summary>Elektrik & Temperaturen</summary><div class="electric-grid">${fields.map(([name, value, key], index) => this._valueLink(`<span>${esc(name)}</span><strong>${esc(value)}</strong>`, this._telemetryIds(...(index === 2 || index === 3 ? [`${s}_ac_raw`, `${s}_dc`, `${s}_power`] : [`${s}_${key}`])), name, "electric-value")).join("")}</div><p class="slot-note">${esc(electrical.note)}</p><label class="fan-row"><span>${slot === "A" ? "Lüfter Venus A" : "Lüfter WR & Speicher"}</span><input type="checkbox" data-fan="${esc(a._config.entities[`${s}_fan`])}" ${fan?.state === "on" ? "checked" : ""} ${!this._available(fan) ? "disabled" : ""}></label></details>`;
  }

  _overview() {
    return `<main class="grid overview">${this._systemCard()}<section class="card span-full">${this._cardTitle("mdi:battery-high", "Speicher")}<div class="battery-pair">${this._models().map(slot => this._batteryCard(slot)).join("")}</div><div class="comparison-grid">${this._models().map(slot => this._comparison(slot, slot.toLowerCase())).join("")}</div></section>${this._planningCard()}</main>`;
  }

  _planningCard() {
    return super._planningCard().replace("plan-card span-5", "plan-card span-full");
  }

  _control() {
    return super._control().replace(/<div class="control-columns manual-columns span-full">[\s\S]*?<\/div>(?=<section class="card span-full">)/, "");
  }

  _diagnostics() {
    const mode = this._state("betriebsart")?.state || this._attr("status", "betriebsart", "—");
    const system = `<section class="card span-full">${this._cardTitle("mdi:shield-check-outline", "System & Betrieb")}<div class="system-diagnostics">${this._diagLine("Version", this._config().version)}${this._diagLine("Betriebsart", mode)}${this._diagLine("Regelung", this._attr("planung", "rueckgabe_ausstehend", false) ? "Grenzwerte werden zurückgegeben" : this._attr("status", "schreibzugriffe_aktiv", false) ? "Schreibzugriffe aktiv" : "Beobachten")}${this._diagLine("Fahrplan", this._statusLabel(this._state("planung")?.state))}${this._diagLine("Mittagsspitze", this._attr("planung", "mittagsspitzen_aktiv", false) ? "Aktiv" : "Aus")}${this._diagLine("Kalibrierung", this._state("kalibrierung")?.state)}</div>${this._calibrationJobsCard()}</section>`;
    return super._diagnostics().replace('<main class="grid diagnostics-view">', `<main class="grid diagnostics-view">${system}`);
  }

  _render() {
    if (!this.isConnected || !this._hass || !this._cardConfig) return;
    if (!this._panel) {
      this.shadowRoot.innerHTML = `<style>${this._styles()}</style><section class="card load-state"><strong>${esc(this._loadError || "Konfiguration wird geladen …")}</strong><p>Speicher-Ladelogik A/E ab 2.3.0 muss eingerichtet sein.</p><button class="action-btn" data-retry>Erneut versuchen</button></section>`;
      this._applyAppearance();
      this.shadowRoot.querySelector("[data-retry]")?.addEventListener("click", () => { this._nextResolve = 0; this._loadConfig(); });
      return;
    }
    if (this._rendered && (this._manualBusy.size || this.shadowRoot.activeElement?.closest?.("[data-manual-form]"))) {
      this._renderDeferred = true;
      this._refreshLive();
      return;
    }
    for (const [slot, draft] of this._manualDrafts) if (!draft.dirty) this._manualDrafts.delete(slot);
    super._render();
    if (this._tab === "overview") {
      const analytics = this._getAnalytics(); analytics.hass = this._hass;
      if (analytics.parentNode !== this._analyticsHost) this._analyticsHost.append(analytics);
    }
    this._analyticsHost.hidden = this._tab !== "overview";
    this._renderDeferred = false;
  }

  _commitRender(html) {
    // Never detach the Recorder controls during a live update. Reattaching the
    // same node preserves values but still closes native date/time pickers.
    if (!this._surface?.isConnected) {
      this._surface = document.createElement("div");
      this._analyticsHost = document.createElement("div");
      this._analyticsHost.className = "analytics-host";
      this.shadowRoot.replaceChildren(this._surface, this._analyticsHost);
    }
    this._surface.innerHTML = html;
  }

  _bind() {
    super._bind();
    const wrapValue = (el, ids, label) => {
      if (el.querySelector("button,input,select")) return;
      const button = document.createElement("button");
      button.type = "button"; button.className = "value-link";
      button.dataset.valueSources = JSON.stringify(ids.filter(Boolean));
      button.setAttribute("aria-label", `${label} · Entität oder Quellen öffnen`);
      button.append(...el.childNodes); el.append(button);
    };
    this.shadowRoot.querySelectorAll(".diag-line strong").forEach(el => {
      const label = el.previousElementSibling?.textContent || "Status";
      const key = label === "Kalibrierung" ? "kalibrierung" : label === "Fahrplan" ? "planung" : label === "Betriebsart" ? "betriebsart" : "status";
      wrapValue(el, [this._eid(key)], label);
    });
    this.shadowRoot.querySelectorAll(".decision-card dd").forEach(el => {
      const label = el.previousElementSibling?.textContent || "Planung";
      const slot = el.closest(".storage-a") ? "a" : "e";
      wrapValue(el, [this._eid(label === "Bevorzugt" ? `bevorzugte_ladeleistung_venus_${slot}` : "planung")], label);
    });
    this.shadowRoot.querySelectorAll(".cal-window,.cal-state>div strong,.calibration-card .cal-result>span").forEach(el => {
      wrapValue(el, [this._eid("kalibrierung")], "Kalibrierung");
    });
    this.shadowRoot.querySelectorAll("[data-value-sources]").forEach(button => button.addEventListener("click", event => {
      event.preventDefault(); event.stopPropagation();
      this._openValueSources(JSON.parse(button.dataset.valueSources), button.getAttribute("aria-label") || "Quellen");
    }));
    this.shadowRoot.querySelectorAll("[data-info]").forEach(button => button.addEventListener("click", event => {
      event.preventDefault(); event.stopPropagation(); const id = button.dataset.info; if (id && id !== "null") this._moreInfo(id);
    }));
    this.shadowRoot.querySelectorAll("button[data-entity]").forEach(button => button.addEventListener("click", event => {
      event.preventDefault(); event.stopPropagation();
      if (button.dataset.entity && button.dataset.entity !== "null") this._moreInfo(button.dataset.entity);
    }));
    this.shadowRoot.querySelectorAll("[data-manual-form]").forEach(form => {
      const slot = form.dataset.manualForm;
      const update = () => {
        const draft = this._draftFor(slot);
        draft.active = form.querySelector("[data-manual-active]").checked;
        draft.mode = form.querySelector("[data-device-mode]").value;
        form.querySelectorAll("[data-manual-range]").forEach(input => {
          draft[input.dataset.manualRange] = Number(input.value);
          form.querySelector(`[data-output="${input.dataset.manualRange}"]`).textContent = this._power(Number(input.value));
        });
        draft.dirty = true;
        form.querySelector("[data-manual-feedback]").textContent = draft.active || draft.originalActive ? "Änderungen noch nicht übernommen." : "Zum Ändern der Grenzen Handbetrieb einschalten und übernehmen.";
        form.querySelector("[data-apply-manual]").disabled = !draft.active && !draft.originalActive;
      };
      form.querySelectorAll("input,select").forEach(input => input.addEventListener(input.type === "range" ? "input" : "change", update));
      form.querySelector("[data-apply-manual]").addEventListener("click", () => this._applyManual(slot));
      // Wait for the next task: a microtask between blur and focus can replace
      // the button before its click arrives when a live update was deferred.
      form.addEventListener("focusout", () => setTimeout(() => {
        if (this._renderDeferred && !this.shadowRoot.activeElement?.closest?.("[data-manual-form]")) this._render();
      }, 0));
    });
    this.shadowRoot.querySelectorAll("[data-fan]").forEach(input => input.addEventListener("change", async () => {
      input.disabled = true;
      try { await this._hass.callService("switch", input.checked ? "turn_on" : "turn_off", { entity_id: input.dataset.fan }); }
      catch (error) { input.checked = !input.checked; this._toast(error.message || "Lüfter konnte nicht geschaltet werden."); }
      finally { input.disabled = false; }
    }));
  }

  async _applyManual(slot) {
    if (this._manualBusy.has(slot) || this._hass?.user?.is_admin !== true) return;
    const draft = { ...this._draftFor(slot) };
    if (!draft.dirty) return;
    const suffix = slot.toLowerCase(), mode = this._getAnalytics()._state(`${suffix}_mode`);
    if (draft.active && [draft.charge, draft.discharge].some(value => !finite(value))) { this._toast("Beide Leistungsgrenzen müssen gültig sein."); return; }
    const modeChanged = draft.active && mode && draft.mode !== mode.state;
    if (modeChanged && !mode.attributes?.options?.includes(draft.mode)) { this._toast("Betriebsmodus ist nicht mehr verfügbar."); return; }
    this._manualBusy.add(slot);
    const form = this.shadowRoot.querySelector(`[data-manual-form="${slot}"]`);
    form?.querySelectorAll("input,select,button").forEach(el => el.disabled = true);
    let limitsApplied = false;
    try {
      await this._hass.callService("speicher_ladelogik_ae", "apply_manual", {
        entry_id: this._config().entry_id, battery: slot, active: draft.active,
        ...(draft.active ? { charge_w: draft.charge, discharge_w: draft.discharge } : {}),
      });
      limitsApplied = true;
      if (modeChanged) await this._hass.callService("select", "select_option", { entity_id: mode.entity_id || this._getAnalytics()._config.entities[`${suffix}_mode`], option: draft.mode });
      this._manualDrafts.delete(slot);
      this._messages.set(slot, draft.active ? "Handbetriebswerte übernommen. Gerätegrenzen und Sicherheitsprüfungen bleiben aktiv." : "Handbetrieb beendet. Die Ladelogik übernimmt wieder.");
      this._toast(this._messages.get(slot));
    } catch (error) {
      this._messages.set(slot, `${limitsApplied ? "Handbetriebswerte übernommen, Betriebsmodus fehlgeschlagen. " : "Nicht übernommen. "}${error.message || "Schreibfehler"}`);
      this._toast(this._messages.get(slot));
    } finally {
      this._manualBusy.delete(slot);
      this.shadowRoot.activeElement?.blur?.();
      this._rendered = false;
      this._render();
    }
  }

  _toast(message) { this.dispatchEvent(new CustomEvent("hass-notification", { bubbles: true, composed: true, detail: { message } })); }

  _refreshLive() {
    if (!this._panel) return;
    super._refreshLive();
    const d = this._summaryData();
    this._setLiveText("[data-live-combined]", finite(d.soc) ? String(Math.round(d.soc)) : "—");
    this._setLiveText("[data-summary-energy]", finite(d.energy) ? this._energy(d.energy) : "—");
    this._setLiveText("[data-summary-power]", finite(d.power) ? this._power(Math.abs(d.power) * 1000) : "—");
    this._models().forEach(slot => {
      const s = slot.toLowerCase(), soc = this._entityNum(this._source(`soc_${s}`), NaN);
      this.shadowRoot.querySelector(`[data-track="${s}"]`)?.style.setProperty("width", `${finite(soc) ? soc : 0}%`);
    });
  }

  _styles() {
    return super._styles() + `
      :host{font:14px/1.45 Arial,Helvetica,sans-serif;min-height:0;background:#eef2f6;--card:#fff;--surface:#f4f6f9;--muted:#526276;--line:#dfe5ec;--primary-text-color:#172435;border-radius:18px;padding:22px;container-type:inline-size;color-scheme:light}
      :host([data-theme="light"]){--primary-background-color:#eef2f6;--primary-text-color:#172435;--card:#fff;--surface:#f4f6f9;--muted:#526276;--line:#dfe5ec;background:#eef2f6}
      :host([data-theme="dark"]){--primary-background-color:#10151e;--primary-text-color:#ecf1f8;--card:#1b2330;--surface:#25303f;--muted:#a9b8ca;--line:#344051;background:#10151e;color-scheme:dark}
      header.cockpit-header{position:static;min-height:0;padding:0 0 20px;border:0;background:transparent;gap:15px;display:flex}.brand-copy strong{font:500 26px/1.2 Arial;letter-spacing:-.5px}.brand-copy span{font-size:12px;margin-top:5px}.appearance-toggle{margin-left:auto}
      main.grid{padding:0;max-width:none;gap:16px}.card{border:0;border-radius:13px;padding:18px;box-shadow:none}.card-title{font-weight:500;font-size:12px;letter-spacing:.05em}.card-title>span{text-transform:uppercase}.card-title ha-icon{display:none}.summary-grid{display:grid;grid-template-columns:180px 1fr 1fr;align-items:center}.soc-ring{width:140px;height:140px}.soc-ring:before{inset:12px}.soc-ring strong{font-size:37px}.soc-ring small{font-size:16px}.summary-metric{border-left:1px solid var(--line);padding:18px 24px}.summary-metric>span,.summary-metric small{display:block;font-size:11px;color:var(--muted)}.summary-metric strong{display:block;font-size:29px;font-weight:500;margin:10px 0 5px;letter-spacing:-.4px}.summary-status{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px;padding-top:15px;border-top:1px solid var(--line)}.summary-status .status-line{background:var(--surface);padding:12px;border:0;border-radius:9px}.badge{border:0}
      .battery-pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}.battery-card{border:1px solid var(--line);border-top:4px solid var(--storage-color);border-radius:12px;padding:17px;background:var(--card);min-width:0}.battery-heading,.battery-current{display:flex;align-items:center;justify-content:space-between;gap:12px}.battery-heading h3{margin:0;font-size:18px;font-weight:500}.battery-current{margin:20px 0 12px;align-items:flex-end}.battery-soc{font-size:38px;font-weight:500;letter-spacing:-1px;color:var(--storage-color)}.battery-power{text-align:right}.battery-power strong{display:block;font-size:24px;font-weight:500}.battery-power span{font-size:11px;color:var(--muted)}.battery-track{height:7px;border-radius:7px;background:var(--surface);overflow:hidden}.battery-track i{display:block;height:100%;background:var(--storage-color)}.battery-caption{display:flex;justify-content:space-between;gap:9px;font-size:10px;color:var(--muted);margin-top:7px}.battery-card .cal-result{padding:10px;background:var(--surface);border:0}.battery-card .metric-pairs{grid-template-columns:1fr 1fr;margin-top:14px;gap:9px}.metric{background:var(--surface);padding:10px;border-radius:9px;min-width:0}.metric ha-icon{display:none}.metric span{font-size:10px}.metric strong{font-size:14px;font-weight:500}.detail-grid{border-top:1px solid var(--line);padding-top:14px;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 10px}.detail span{font-size:10px}.detail strong{font-size:12px;font-weight:400}.comparison-grid{margin-top:15px}.comparison{padding:12px;background:var(--surface);border-radius:9px}
      .device-controls,.electrical-details{border-top:1px solid var(--line);margin-top:15px}.electrical-details{margin-top:0}summary{cursor:pointer;color:var(--muted);font-size:13px;padding:14px 0;min-height:44px}.manual-toggle{display:flex;justify-content:space-between;align-items:center;gap:15px;background:var(--surface);padding:12px;border-radius:9px}.manual-toggle strong{display:block;font-weight:500;font-size:12px}.manual-toggle small{display:block;font-size:10px;color:var(--muted);margin-top:4px}.manual-toggle input{width:20px;height:20px;accent-color:var(--storage-color)}.device-mode{display:block;font-size:12px;color:var(--muted);margin-top:16px}.device-mode select{display:block;width:100%;max-width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--primary-text-color);margin-top:7px;font:inherit}.manual-range{display:block;margin:19px 0;color:var(--muted)}.manual-range>span{display:flex;align-items:center;gap:8px;font-size:12px}.manual-range output{margin-left:auto;white-space:nowrap;color:var(--primary-text-color)}.manual-range input{display:block;width:100%;margin:16px 0 8px;accent-color:var(--storage-color)}.manual-range small{font-size:10px}.source-button{background:none;border:0;color:var(--storage-color);font-size:17px;padding:0 2px}.manual-apply{display:flex;align-items:center;justify-content:space-between;gap:15px;padding-bottom:15px}.manual-apply>span{font-size:10px;color:var(--muted);line-height:1.5}.action-btn{border:1px solid var(--line);background:var(--surface);color:var(--primary-text-color);border-radius:8px;min-height:38px;cursor:pointer}.action-btn:disabled{opacity:.5;cursor:default}.electric-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:17px 10px;padding:5px 0 13px}.electric-value{min-width:0;padding:0;text-align:left;background:none;border:0;color:inherit;cursor:pointer}.electric-value span{display:block;font-size:10px;color:var(--muted);line-height:1.4}.electric-value strong{display:block;font-size:13px;font-weight:400;margin-top:6px}.fan-row{border-top:1px solid var(--line);padding:13px 0;display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted)}.fan-row input{accent-color:var(--storage-color);width:18px;height:18px}.system-diagnostics{display:grid;grid-template-columns:1fr 1fr;gap:0 25px}.load-state{margin:10px}
      .overview>.plan-card{grid-column:1/-1}.plan-card>.metric-pairs{grid-template-columns:repeat(4,minmax(0,1fr))}
      @container(max-width:820px){.battery-pair{grid-template-columns:1fr}.summary-grid{grid-template-columns:150px 1fr 1fr}.summary-metric{padding:16px}.summary-metric strong{font-size:23px}.plan-card>.metric-pairs{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @container(max-width:540px){.summary-grid,.summary-status{grid-template-columns:1fr}.soc-ring{margin:0 auto 20px}.summary-metric{border-left:0;border-top:1px solid var(--line);text-align:center;padding:21px 0}.summary-status{margin-top:0}.battery-caption{font-size:10px}.system-diagnostics{grid-template-columns:1fr}.brand-copy strong{font-size:21px}.electric-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
      @media(max-width:600px){:host{padding:13px}.card{padding:15px}.battery-card{padding:13px}.detail-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
      .analytics-host{margin-top:16px}.analytics-host[hidden]{display:none}
      .value-link{font:inherit;color:inherit;background:none;border:0;margin:0;padding:0;text-align:inherit;cursor:pointer;min-width:0;max-width:100%;overflow-wrap:anywhere}
      .value-link:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.soc-ring .value-link{position:relative;z-index:1;text-align:center;display:flex;flex-direction:column;align-items:center;gap:6px}.soc-ring .value-link>span{display:block}
      .summary-metric>.value-link,.battery-power>.value-link{display:block;width:100%}.battery-power>span{display:block;margin-top:4px}
      .metric-pairs>.metric,.peak-layout>.metric{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:7px;text-align:left;width:100%;padding:12px;min-height:72px;background:var(--surface);border-radius:9px}
      .metric-pairs>.metric>span,.peak-layout>.metric>span{grid-area:auto;display:block;width:100%;font-size:11px;line-height:1.4;white-space:normal}
      .metric-pairs>.metric>strong,.peak-layout>.metric>strong{grid-area:auto;display:block;width:100%;font-size:14px;line-height:1.4;white-space:normal}
      .detail-grid>.detail.value-link{display:flex;flex-direction:column;gap:7px;padding:10px;background:var(--surface);border-radius:9px;text-align:left}.detail-grid>.detail.value-link>strong{margin:0;line-height:1.5}
      .battery-card .cal-result.value-link{display:flex;flex-direction:column;align-items:flex-start;width:100%;text-align:left;gap:5px}.battery-caption>.value-link{font-size:inherit;color:inherit}
      .number-row>div:first-of-type{position:relative;padding-right:20px}.setting-source{position:absolute;right:0;top:0;color:var(--accent);font-size:18px}
      .value-sources{max-width:min(580px,calc(100vw - 32px));max-height:80vh;overflow:auto;box-sizing:border-box;border:1px solid var(--line);border-radius:12px;padding:20px;background:var(--card);color:var(--primary-text-color);font:inherit}.value-sources::backdrop{background:#0005}.value-sources h3{margin:0 0 12px}.value-sources p{font-size:13px;color:var(--muted)}.value-source-row{display:flex;flex-direction:column;gap:6px;text-align:left;width:100%;padding:12px;margin:10px 0;background:var(--surface);color:inherit;border:1px solid var(--line);border-radius:8px;cursor:pointer;overflow-wrap:anywhere}.value-source-row small{color:var(--muted)}
    `;
  }
}

if (!customElements.get(TAG)) customElements.define(TAG, SpeicherLadelogikCard);
window.customCards ||= [];
if (!window.customCards.some(card => card.type === TAG)) window.customCards.push({ type: TAG, name: "Speicher-Ladelogik A/E", description: "Übersicht, Kalibrierung, Steuerung und Diagnose als normale Lovelace-Karte.", preview: false });
export { SpeicherLadelogikCard };
