const CARD_VERSION = "0.6.0";

class UnitreeGo2Card extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._render();
      this._rendered = true;
    }
    this._update();
  }

  setConfig(config) {
    this._config = {
      entity_prefix: "",
      name: "Go2",
      show_camera: true,
      show_vision: true,
      show_sliders: true,
      ...config,
    };
    this._rendered = false;
  }

  getCardSize() {
    return 8;
  }

  static getStubConfig() {
    return { entity_prefix: "", name: "Go2" };
  }

  _eid(suffix) {
    return suffix.replace("{p}", this._config.entity_prefix);
  }

  _state(domain, key) {
    const eid = `${domain}.${this._config.entity_prefix}_${key}`;
    const s = this._hass?.states[eid];
    return s ? s.state : "unavailable";
  }

  _stateNum(domain, key, fallback = 0) {
    const v = this._state(domain, key);
    const n = parseFloat(v);
    return isNaN(n) ? fallback : n;
  }

  _callService(domain, service, data = {}) {
    this._hass.callService(domain, service, data);
  }

  _pressButton(key) {
    this._callService("button", "press", {
      entity_id: `button.${this._config.entity_prefix}_${key}`,
    });
  }

  _toggleSwitch(key) {
    const eid = `switch.${this._config.entity_prefix}_${key}`;
    const current = this._hass.states[eid]?.state;
    this._callService("switch", current === "on" ? "turn_off" : "turn_on", {
      entity_id: eid,
    });
  }

  _render() {
    if (this.shadowRoot) this.shadowRoot.innerHTML = "";
    const shadow = this.attachShadow
      ? this.shadowRoot || this.attachShadow({ mode: "open" })
      : this;

    shadow.innerHTML = `
      <style>
        :host {
          --card-bg: var(--ha-card-background, var(--card-background-color, #fff));
          --primary: var(--primary-text-color, #212121);
          --secondary: var(--secondary-text-color, #727272);
          --accent: var(--primary-color, #03a9f4);
          --green: #4caf50;
          --red: #f44336;
          --orange: #ff9800;
          --divider: var(--divider-color, rgba(0,0,0,0.12));
        }
        ha-card {
          overflow: hidden;
          font-family: var(--ha-card-font-family, inherit);
        }
        /* Header */
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 16px 8px;
        }
        .header-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .robot-icon {
          font-size: 24px;
        }
        .robot-name {
          font-size: 18px;
          font-weight: 500;
          color: var(--primary);
        }
        .header-right {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 14px;
        }
        .battery {
          display: flex;
          align-items: center;
          gap: 4px;
          font-weight: 500;
        }
        .battery-icon {
          font-size: 18px;
        }
        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
        }
        .status-dot.online { background: var(--green); }
        .status-dot.offline { background: var(--red); }
        .status-dot.unavailable { background: var(--secondary); }

        /* Camera */
        .camera-container {
          position: relative;
          width: 100%;
          aspect-ratio: 16/9;
          background: #000;
          overflow: hidden;
          cursor: pointer;
        }
        .camera-container img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }
        .camera-offline {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
          color: var(--secondary);
          font-size: 14px;
        }

        /* Info bar */
        .info-bar {
          display: flex;
          justify-content: space-around;
          padding: 8px 16px;
          border-bottom: 1px solid var(--divider);
          font-size: 13px;
          color: var(--secondary);
        }
        .info-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        /* Controls */
        .controls {
          display: flex;
          padding: 12px 16px;
          gap: 16px;
          align-items: center;
        }
        .dpad {
          display: grid;
          grid-template-columns: 40px 40px 40px;
          grid-template-rows: 40px 40px 40px;
          gap: 2px;
          flex-shrink: 0;
        }
        .dpad-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--card-bg);
          border: 1px solid var(--divider);
          border-radius: 8px;
          cursor: pointer;
          font-size: 18px;
          color: var(--primary);
          transition: background 0.15s;
          padding: 0;
        }
        .dpad-btn:hover { background: var(--divider); }
        .dpad-btn:active { background: var(--accent); color: #fff; }
        .dpad-center {
          background: none;
          border: none;
          cursor: default;
          font-size: 12px;
          color: var(--secondary);
        }
        .dpad-center:hover { background: none; }

        .quick-actions {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          gap: 6px;
          flex: 1;
        }
        .action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 4px;
          padding: 8px 4px;
          background: var(--card-bg);
          border: 1px solid var(--divider);
          border-radius: 8px;
          cursor: pointer;
          font-size: 12px;
          color: var(--primary);
          transition: background 0.15s;
          white-space: nowrap;
        }
        .action-btn:hover { background: var(--divider); }
        .action-btn:active { background: var(--accent); color: #fff; }
        .action-btn.stop {
          background: var(--red);
          color: #fff;
          border-color: var(--red);
          font-weight: 600;
        }
        .action-btn.stop:hover { opacity: 0.85; }

        /* Vision */
        .vision {
          padding: 8px 16px;
          border-top: 1px solid var(--divider);
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--secondary);
        }
        .vision-text {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: var(--primary);
        }

        /* Sliders */
        .sliders {
          padding: 8px 16px 4px;
          border-top: 1px solid var(--divider);
        }
        .slider-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
          font-size: 13px;
          color: var(--secondary);
        }
        .slider-label {
          width: 20px;
          text-align: center;
        }
        .slider-row input[type=range] {
          flex: 1;
          height: 4px;
          -webkit-appearance: none;
          appearance: none;
          background: var(--divider);
          border-radius: 2px;
          outline: none;
        }
        .slider-row input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: var(--accent);
          cursor: pointer;
        }
        .slider-value {
          width: 28px;
          text-align: right;
          font-size: 12px;
        }

        /* Switches */
        .switches {
          display: flex;
          justify-content: center;
          gap: 12px;
          padding: 8px 16px 14px;
          border-top: 1px solid var(--divider);
        }
        .switch-pill {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          user-select: none;
        }
        .switch-pill.on {
          background: var(--accent);
          color: #fff;
        }
        .switch-pill.off {
          background: var(--divider);
          color: var(--secondary);
        }
        .switch-pill .dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .switch-pill.on .dot { background: #fff; }
        .switch-pill.off .dot { background: var(--secondary); }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-left">
            <span class="robot-icon">&#x1F415;</span>
            <span class="robot-name" id="name"></span>
          </div>
          <div class="header-right">
            <span class="battery">
              <span class="battery-icon" id="bat-icon">&#x1F50B;</span>
              <span id="bat-pct">—%</span>
            </span>
            <span class="status-dot" id="status-dot"></span>
          </div>
        </div>

        <div class="camera-container" id="camera-container">
          <div class="camera-offline" id="camera-offline">Kamera nicht verfügbar</div>
        </div>

        <div class="info-bar">
          <span class="info-item"><span>&#x1F321;</span> <span id="temp">—</span>°C</span>
          <span class="info-item"><span>&#x26A1;</span> <span id="voltage">—</span>V</span>
          <span class="info-item"><span>&#x1F3C3;</span> <span id="mode">—</span></span>
        </div>

        <div class="controls">
          <div class="dpad">
            <div></div>
            <button class="dpad-btn" id="btn-fwd">&#x25B2;</button>
            <div></div>
            <button class="dpad-btn" id="btn-left">&#x25C0;</button>
            <button class="dpad-btn dpad-center">&#x1F43E;</button>
            <button class="dpad-btn" id="btn-right">&#x25B6;</button>
            <div></div>
            <button class="dpad-btn" id="btn-back">&#x25BC;</button>
            <div></div>
          </div>
          <div class="quick-actions">
            <button class="action-btn" id="act-standlock">Aufstehen</button>
            <button class="action-btn" id="act-sit">Sitzen</button>
            <button class="action-btn" id="act-classic">Classic</button>
            <button class="action-btn" id="act-freewalk">Free Walk</button>
            <button class="action-btn" id="act-hello">Pfote</button>
            <button class="action-btn stop" id="act-stop">&#x1F6D1; STOP</button>
          </div>
        </div>

        <div class="vision" id="vision-row" style="display:none;">
          <span>&#x1F441;</span>
          <span class="vision-text" id="vision-text">—</span>
        </div>

        <div class="sliders" id="sliders-section">
          <div class="slider-row">
            <span class="slider-label">&#x1F50A;</span>
            <input type="range" min="0" max="10" step="1" id="slider-vol">
            <span class="slider-value" id="val-vol">—</span>
          </div>
          <div class="slider-row">
            <span class="slider-label">&#x1F4A1;</span>
            <input type="range" min="0" max="10" step="1" id="slider-light">
            <span class="slider-value" id="val-light">—</span>
          </div>
        </div>

        <div class="switches">
          <div class="switch-pill off" id="sw-cmd">
            <span class="dot"></span>
            <span>Befehle</span>
          </div>
          <div class="switch-pill off" id="sw-move">
            <span class="dot"></span>
            <span>Bewegung</span>
          </div>
        </div>
      </ha-card>
    `;

    // D-Pad
    shadow.getElementById("btn-fwd").addEventListener("click", () => this._pressButton("vorwarts"));
    shadow.getElementById("btn-back").addEventListener("click", () => this._pressButton("ruckwarts"));
    shadow.getElementById("btn-left").addEventListener("click", () => this._pressButton("links"));
    shadow.getElementById("btn-right").addEventListener("click", () => this._pressButton("rechts"));

    // Quick Actions — use select + execute like the device page
    const execCmd = (cmd) => {
      this._callService("select", "select_option", {
        entity_id: `select.${this._config.entity_prefix}_befehl`,
        option: cmd,
      });
      setTimeout(() => this._pressButton("befehl_ausfuhren"), 200);
    };
    shadow.getElementById("act-standlock").addEventListener("click", () => execCmd("Stand Lock / Low Down"));
    shadow.getElementById("act-sit").addEventListener("click", () => execCmd("Sit Down"));
    shadow.getElementById("act-classic").addEventListener("click", () => execCmd("Classic"));
    shadow.getElementById("act-freewalk").addEventListener("click", () => execCmd("Free Walk"));
    shadow.getElementById("act-hello").addEventListener("click", () => execCmd("Shake Hands"));
    shadow.getElementById("act-stop").addEventListener("click", () =>
      this._pressButton("notaus"));

    // Switches
    shadow.getElementById("sw-cmd").addEventListener("click", () =>
      this._toggleSwitch("befehle"));
    shadow.getElementById("sw-move").addEventListener("click", () =>
      this._toggleSwitch("bewegung_aktiviert"));

    // Sliders
    const volSlider = shadow.getElementById("slider-vol");
    volSlider.addEventListener("change", (e) => {
      this._callService("number", "set_value", {
        entity_id: `number.${this._config.entity_prefix}_lautstarke`,
        value: parseFloat(e.target.value),
      });
    });
    const lightSlider = shadow.getElementById("slider-light");
    lightSlider.addEventListener("change", (e) => {
      this._callService("number", "set_value", {
        entity_id: `number.${this._config.entity_prefix}_kopflicht`,
        value: parseFloat(e.target.value),
      });
    });

    // Camera click
    shadow.getElementById("camera-container").addEventListener("click", () => {
      const camEntity = `camera.${this._config.entity_prefix}_kamera`;
      const event = new Event("hass-more-info", { bubbles: true, composed: true });
      event.detail = { entityId: camEntity };
      this.dispatchEvent(event);
    });

    this._cameraInterval = setInterval(() => this._updateCamera(), 5000);
    this._updateCamera();
  }

  _updateCamera() {
    if (!this._hass || !this._config) return;
    const camEntity = `camera.${this._config.entity_prefix}_kamera`;
    const cam = this._hass.states[camEntity];
    const container = this.shadowRoot.getElementById("camera-container");
    const offlineEl = this.shadowRoot.getElementById("camera-offline");

    if (cam && cam.state !== "unavailable") {
      const url = `/api/camera_proxy/${camEntity}?token=${cam.attributes.access_token}&t=${Date.now()}`;
      let img = container.querySelector("img");
      if (!img) {
        img = document.createElement("img");
        img.alt = "Go2 Camera";
        container.appendChild(img);
      }
      img.src = url;
      offlineEl.style.display = "none";
      img.style.display = "block";
    } else {
      const img = container.querySelector("img");
      if (img) img.style.display = "none";
      offlineEl.style.display = "flex";
    }
  }

  _update() {
    if (!this.shadowRoot || !this._config || !this._hass) return;
    const $ = (id) => this.shadowRoot.getElementById(id);

    // Name
    $("name").textContent = this._config.name;

    // Battery
    const bat = this._stateNum("sensor", "batterie", -1);
    if (bat >= 0) {
      $("bat-pct").textContent = `${Math.round(bat)}%`;
      $("bat-icon").textContent = bat > 75 ? "\u{1F50B}" : bat > 25 ? "\u{1FAAB}" : "\u{1FAAB}";
      $("bat-pct").style.color = bat < 20 ? "var(--red)" : bat < 40 ? "var(--orange)" : "";
    } else {
      $("bat-pct").textContent = "—%";
    }

    // Online status
    const online = this._state("binary_sensor", "online");
    const dot = $("status-dot");
    dot.className = `status-dot ${online === "on" ? "online" : online === "off" ? "offline" : "unavailable"}`;

    // Info bar
    const temp = this._stateNum("sensor", "gehause_temp", -1);
    $("temp").textContent = temp >= 0 ? temp.toFixed(0) : "—";
    const volt = this._stateNum("sensor", "bus_spannung", -1);
    $("voltage").textContent = volt >= 0 ? volt.toFixed(1) : "—";
    $("mode").textContent = this._state("sensor", "modus") || "—";

    // Vision
    if (this._config.show_vision) {
      const detected = this._state("sensor", "vision_erkannte_objekte");
      const desc = this._state("sensor", "vision_letzte_beschreibung");
      const visionRow = $("vision-row");
      const visionText = $("vision-text");
      if (detected && detected !== "unavailable" && detected !== "unknown" && detected !== "none") {
        visionText.textContent = detected;
        visionRow.style.display = "flex";
      } else if (desc && desc !== "unavailable" && desc !== "unknown") {
        visionText.textContent = desc;
        visionRow.style.display = "flex";
      } else {
        visionRow.style.display = "none";
      }
    }

    // Sliders
    const vol = this._stateNum("number", "lautstarke", -1);
    if (vol >= 0) {
      $("slider-vol").value = vol;
      $("val-vol").textContent = Math.round(vol);
    }
    const light = this._stateNum("number", "kopflicht", -1);
    if (light >= 0) {
      $("slider-light").value = light;
      $("val-light").textContent = Math.round(light);
    }

    // Switches
    const cmdState = this._state("switch", "befehle");
    const moveState = this._state("switch", "bewegung_aktiviert");
    $("sw-cmd").className = `switch-pill ${cmdState === "on" ? "on" : "off"}`;
    $("sw-move").className = `switch-pill ${moveState === "on" ? "on" : "off"}`;
  }

  disconnectedCallback() {
    if (this._cameraInterval) clearInterval(this._cameraInterval);
  }
}

customElements.define("unitree-go2-card", UnitreeGo2Card);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "unitree-go2-card",
  name: "Unitree Go2",
  description: "Control card for the Unitree Go2 robot dog",
  preview: true,
});

console.info(`%c UNITREE-GO2-CARD %c v${CARD_VERSION} `, "background:#03a9f4;color:#fff;font-weight:bold;", "background:#eee;color:#333;");
