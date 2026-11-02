let KEYBOARDS = null;
let currentKb = 'glove80';
let currentLayer = 0;
let viewerMode = 'simulate'; // Default mode is Simulate
let simStack = [0]; // Active layer indices in simulation mode
let momentaryHoverLayer = null;
let momentaryHoverTriggerIdx = null;
let rgbFadeTimer = null;
let layerHistory = [];
let currentScale = 1.0;
let currentPanX = 0;
let currentPanY = 0;
const MIN_SCALE = 0.6;
const MAX_SCALE = 4.0;
let isTouchDragging = false;
let searchQuery = '';

const UNIT = 54;
const KEY_SIZE = 48;

async function loadData() {
  const embedded = document.getElementById('embedded-data');
  if (embedded && embedded.textContent.trim()) {
    try {
      KEYBOARDS = JSON.parse(embedded.textContent);
      return;
    } catch (e) {
      console.warn('Failed parsing embedded-data:', e);
    }
  }

  try {
    const res = await fetch('data.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    KEYBOARDS = await res.json();
  } catch (err) {
    console.error('Failed to load data.json:', err);
    const container = document.querySelector('.viewport-container');
    if (container) {
      container.innerHTML = `
        <div style="padding: 32px; text-align: center; color: #ff7b72; background: rgba(22, 27, 34, 0.95); border: 1px solid #30363d; border-radius: 12px; max-width: 520px; margin: 40px auto; box-shadow: 0 8px 24px rgba(0,0,0,0.4);">
          <h3 style="margin-bottom: 12px; color: #f85149; font-size: 1.15rem;">⚠️ Unable to load layout data</h3>
          <p style="font-size: 0.88rem; color: #c9d1d9; margin-bottom: 16px; line-height: 1.5;">
            If you opened this HTML file directly via <code>file://</code>, browser security policies restrict loading external <code>data.json</code>.
          </p>
          <p style="font-size: 0.85rem; color: #8b949e; line-height: 1.5;">
            Please run the local viewer server:<br>
            <code style="display: inline-block; margin-top: 10px; padding: 6px 14px; background: #090d12; border: 1px solid #30363d; border-radius: 6px; color: #58a6ff; font-family: monospace;">python3 viewer/serve.py 8088</code>
          </p>
        </div>
      `;
    }
  }
}

function readUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const kbParam = params.get('kb');
  if (kbParam && KEYBOARDS && KEYBOARDS[kbParam.toLowerCase()]) {
    currentKb = kbParam.toLowerCase();
  }
  const modeParam = params.get('mode');
  if (modeParam && ['simulate', 'inspect'].includes(modeParam.toLowerCase())) {
    viewerMode = modeParam.toLowerCase();
  }
  const layerParam = params.get('layer');
  if (layerParam !== null && KEYBOARDS && KEYBOARDS[currentKb]) {
    const kb = KEYBOARDS[currentKb];
    let lIdx = parseInt(layerParam, 10);
    if (isNaN(lIdx)) {
      lIdx = kb.layers.findIndex(l => l.name.toLowerCase() === layerParam.toLowerCase());
    }
    if (lIdx >= 0 && lIdx < kb.layers.length) {
      if (viewerMode === 'simulate') {
        if (!simStack.includes(lIdx)) simStack.push(lIdx);
      } else {
        currentLayer = lIdx;
      }
    }
  }
  const zenParam = params.get('zen');
  if (zenParam === '1' || zenParam === 'true') {
    toggleZenMode();
  }
}

function updateUrlParams() {
  const params = new URLSearchParams();
  params.set('kb', currentKb);
  params.set('mode', viewerMode);
  if (viewerMode === 'inspect') {
    if (currentLayer !== 0) params.set('layer', currentLayer);
  } else if (viewerMode === 'simulate') {
    if (simStack.length > 1) {
      params.set('layer', simStack[simStack.length - 1]);
    }
  }
  const qs = params.toString();
  const newUrl = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState(null, '', newUrl);
}

async function init() {
  await loadData();
  if (!KEYBOARDS) return;

  readUrlParams();
  document.getElementById('btn-glove80').classList.toggle('active', currentKb === 'glove80');
  document.getElementById('btn-go60').classList.toggle('active', currentKb === 'go60');
  document.getElementById('btn-mode-sim').classList.toggle('active', viewerMode === 'simulate');
  document.getElementById('btn-mode-inspect').classList.toggle('active', viewerMode === 'inspect');
  const backBtn = document.getElementById('btn-back-layer');
  if (backBtn) {
    backBtn.style.display = (viewerMode === 'simulate' || layerHistory.length === 0) ? 'none' : 'inline-flex';
  }

  renderLayerTabs();
  renderSvg();
  initCanvasGestures();
  updateHeader();
  resetInspector();

  const urlParams = new URLSearchParams(window.location.search);
  const rgbParam = urlParams.get('rgb');
  if (rgbParam === 'on' || rgbParam === 'keep' || rgbParam === '1') {
    updateRgbUi(true);
    if (rgbFadeTimer) {
      clearTimeout(rgbFadeTimer);
      rgbFadeTimer = null;
    }
  } else {
    triggerRgbFade();
  }

  const inspParam = urlParams.get('inspect');
  if (inspParam !== null) {
    const idx = parseInt(inspParam, 10);
    if (!isNaN(idx)) {
      inspectKey(idx);
      const keyG = document.querySelector(`.key-group[data-idx="${idx}"] rect.key-cap`);
      if (keyG) {
        keyG.style.stroke = 'var(--accent)';
        keyG.style.strokeWidth = '2px';
      }
    }
  }

  const searchParam = urlParams.get('search');
  if (searchParam) {
    const sInput = document.getElementById('search-input');
    if (sInput) sInput.value = searchParam;
    handleSearch(searchParam);
  }

  const modalParam = urlParams.get('modal');
  if (modalParam === 'colors' || urlParams.get('legend') === '1') {
    toggleLegendModal(true);
  }

  const toolsParam = urlParams.get('tools');
  if (toolsParam === 'open' || toolsParam === '1') {
    toggleCanvasWidget(false);
  } else if (toolsParam === '0' || toolsParam === 'collapsed') {
    toggleCanvasWidget(true);
  }

  updateUrlParams();

  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') {
      if (e.key === 'Escape') {
        e.target.blur();
        e.target.value = '';
        handleSearch('');
      }
      return;
    }

    const modal = document.getElementById('legend-modal');
    if (e.key === 'Escape' && modal && modal.style.display !== 'none') {
      toggleLegendModal(false);
      return;
    }

    if (e.key >= '0' && e.key <= '9') {
      const idx = parseInt(e.key);
      const kb = KEYBOARDS[currentKb];
      if (idx < kb.layers.length) {
        if (viewerMode === 'simulate') {
          toggleSimLayer(idx);
        } else {
          setLayer(idx);
        }
      }
    } else if (e.key === 'g' || e.key === 'G') {
      switchKeyboard('glove80');
    } else if (e.key === 'o' || e.key === 'O') {
      switchKeyboard('go60');
    } else if (e.key === 'r' || e.key === 'R') {
      toggleRgb();
    } else if (e.key === 'm' || e.key === 'M') {
      setViewerMode(viewerMode === 'inspect' ? 'simulate' : 'inspect');
    } else if (e.key === 'c' || e.key === 'C') {
      toggleLegendModal();
    } else if (e.key === 'f' || e.key === 'F') {
      toggleZenMode();
    } else if (e.key === 'i' || e.key === 'I') {
      toggleDrawer();
    } else if (e.key === 't' || e.key === 'T') {
      toggleCanvasWidget();
    } else if (e.key === '/') {
      e.preventDefault();
      document.getElementById('search-input').focus();
    } else if (e.key === 'Escape') {
      if (document.body.classList.contains('zen-mode')) {
        toggleZenMode();
      } else if (currentScale > 1.05 || currentPanX !== 0 || currentPanY !== 0) {
        resetZoom();
      } else if (viewerMode === 'simulate') {
        resetSimStack();
      } else if (layerHistory.length > 0) {
        returnToPreviousLayer();
      } else {
        handleSearch('');
        renderSvg();
        resetInspector();
      }
    }
  });

  // Global pointermove for hover momentary layer exit detection
  document.addEventListener('pointermove', (e) => {
    if (momentaryHoverTriggerIdx !== null) {
      const targetKey = e.target.closest('[data-idx]');
      const hoveredIdx = targetKey ? parseInt(targetKey.getAttribute('data-idx'), 10) : null;
      if (hoveredIdx !== momentaryHoverTriggerIdx) {
        deactivateHoverMomentary();
      }
    }
  });

  document.addEventListener('mouseleave', () => {
    if (momentaryHoverTriggerIdx !== null) {
      deactivateHoverMomentary();
    }
  });

  window.addEventListener('popstate', () => {
    readUrlParams();
    document.getElementById('btn-glove80').classList.toggle('active', currentKb === 'glove80');
    document.getElementById('btn-go60').classList.toggle('active', currentKb === 'go60');
    document.getElementById('btn-mode-sim').classList.toggle('active', viewerMode === 'simulate');
    document.getElementById('btn-mode-inspect').classList.toggle('active', viewerMode === 'inspect');
    renderLayerTabs();
    renderSvg();
    updateHeader();
    resetInspector();
    triggerRgbFade();
  });
}

function updateRgbUi(isLit) {
  const svg = document.getElementById('keyboard-svg');
  const btn = document.getElementById('btn-rgb-toggle');
  if (svg) {
    svg.classList.add('rgb-mode');
    if (isLit) {
      svg.classList.remove('rgb-faded');
    } else {
      svg.classList.add('rgb-faded');
    }
  }
  if (btn) {
    btn.classList.toggle('active', isLit);
    btn.title = `RGB Underglow: ${isLit ? 'ON' : 'OFF'} (R)`;
  }
}

function triggerRgbFade() {
  const svg = document.getElementById('keyboard-svg');
  if (!svg) return;

  if (rgbFadeTimer) {
    clearTimeout(rgbFadeTimer);
    rgbFadeTimer = null;
  }

  updateRgbUi(true);

  // Fade out after exactly 1 second (1000ms) in both Simulate and Inspect modes
  rgbFadeTimer = setTimeout(() => {
    updateRgbUi(false);
    rgbFadeTimer = null;
  }, 1000);
}

function toggleRgb() {
  const svg = document.getElementById('keyboard-svg');
  if (!svg) return;

  const isCurrentlyLit = !svg.classList.contains('rgb-faded');
  if (isCurrentlyLit) {
    if (rgbFadeTimer) {
      clearTimeout(rgbFadeTimer);
      rgbFadeTimer = null;
    }
    updateRgbUi(false);
  } else {
    triggerRgbFade();
  }
}

function toggleLegendModal(forceState) {
  const modal = document.getElementById('legend-modal');
  if (!modal) return;
  const isHidden = modal.style.display === 'none';
  const show = (forceState !== undefined) ? forceState : isHidden;
  modal.style.display = show ? 'flex' : 'none';
}

function setViewerMode(mode) {
  if (viewerMode === mode) return;
  viewerMode = mode;
  document.getElementById('btn-mode-inspect').classList.toggle('active', mode === 'inspect');
  document.getElementById('btn-mode-sim').classList.toggle('active', mode === 'simulate');

  const backBtn = document.getElementById('btn-back-layer');
  if (mode === 'simulate') {
    if (backBtn) backBtn.style.display = 'none';
    if (!simStack.includes(0)) simStack = [0];
  } else {
    updateBackButton();
  }

  deactivateHoverMomentary();
  renderLayerTabs();
  renderSvg();
  resetInspector();
  triggerRgbFade();
  updateUrlParams();
}

function switchKeyboard(kb) {
  if (currentKb === kb) return;
  currentKb = kb;
  currentLayer = 0;
  simStack = [0];
  momentaryHoverLayer = null;
  momentaryHoverTriggerIdx = null;
  layerHistory = [];
  resetZoom();
  document.getElementById('btn-glove80').classList.toggle('active', kb === 'glove80');
  document.getElementById('btn-go60').classList.toggle('active', kb === 'go60');
  updateHeader();
  updateBackButton();
  renderLayerTabs();
  renderSvg();
  resetInspector();
  triggerRgbFade();
  updateUrlParams();
}

function updateHeader() {
  const kb = KEYBOARDS[currentKb];
  const match = kb && kb.title ? kb.title.match(/v[0-9]+/) : null;
  document.getElementById('kb-version').textContent = match ? match[0] : '';
}

function getActiveSimLayers() {
  if (momentaryHoverLayer !== null && !simStack.includes(momentaryHoverLayer)) {
    const list = [...simStack, momentaryHoverLayer];
    list.sort((a, b) => a - b);
    return list;
  }
  return simStack;
}

function isLayerTriggerKey(idx, targetLayer) {
  const kb = KEYBOARDS[currentKb];
  if (!kb || !kb.layers) return false;
  // Check if any layer below targetLayer has this key configured to trigger targetLayer
  for (let l = 0; l < targetLayer; l++) {
    const k = kb.layers[l] && kb.layers[l].keys[idx];
    if (k && k.targetLayer === targetLayer) {
      return true;
    }
  }
  return false;
}

function resolveCompositeKey(idx) {
  const kb = KEYBOARDS[currentKb];
  const activeLayers = getActiveSimLayers();
  for (let i = activeLayers.length - 1; i >= 0; i--) {
    const layerIdx = activeLayers[i];

    // If this layer was temporarily previewed by hovering over key `idx`,
    // do not let this previewed layer overwrite key `idx` itself.
    if (layerIdx === momentaryHoverLayer && idx === momentaryHoverTriggerIdx) {
      continue;
    }

    const key = kb.layers[layerIdx] && kb.layers[layerIdx].keys[idx];
    if (key && key.rawBinding !== '&trans' && key.line1 !== '▽') {
      // If the key on this active layer is &none, but this key position was the trigger
      // for this active layer from a lower layer (e.g. Magic key on Base triggering Magic layer),
      // allow it to fall through so the trigger key stays visible and can toggle the layer off!
      if (key.rawBinding === '&none' && isLayerTriggerKey(idx, layerIdx)) {
        continue;
      }
      return { key, sourceLayer: layerIdx };
    }
  }
  const baseKey = kb.layers[0].keys[idx] || { line1: '', line2: '', rawBinding: '' };
  return { key: baseKey, sourceLayer: 0 };
}

function resolveCompositeRgb(idx) {
  const kb = KEYBOARDS[currentKb];
  const activeLayers = getActiveSimLayers();
  for (let i = activeLayers.length - 1; i >= 0; i--) {
    const layerIdx = activeLayers[i];
    if (layerIdx === momentaryHoverLayer && idx === momentaryHoverTriggerIdx) {
      continue;
    }
    const key = kb.layers[layerIdx] && kb.layers[layerIdx].keys[idx];
    if (key && key.rgbToken && key.rgbToken !== '___') {
      return {
        rgbToken: key.rgbToken,
        rgbHex: key.rgbHex,
        rgbSourceLayer: layerIdx
      };
    }
  }
  return { rgbToken: '___', rgbHex: '#000000', rgbSourceLayer: null };
}

function activateHoverMomentary(idx, targetLayer) {
  if (viewerMode !== 'simulate') return;
  // If layer is already active in simStack, no temporary hover preview needed
  if (simStack.includes(targetLayer)) return;
  if (momentaryHoverLayer === targetLayer) return;

  momentaryHoverLayer = targetLayer;
  momentaryHoverTriggerIdx = idx;
  updateLayerTabStates();
  renderSvg();
  triggerRgbFade();
}

function deactivateHoverMomentary() {
  if (momentaryHoverLayer === null) return;
  momentaryHoverLayer = null;
  momentaryHoverTriggerIdx = null;
  updateLayerTabStates();
  renderSvg();
  triggerRgbFade();
}

function resetSimStack() {
  simStack = [0];
  momentaryHoverLayer = null;
  momentaryHoverTriggerIdx = null;
  updateLayerTabStates();
  renderSvg();
  triggerRgbFade();
  updateUrlParams();
}

function toggleSimLayer(layerIdx) {
  if (layerIdx === 0) {
    if (simStack.length > 1) {
      resetSimStack();
    }
    return;
  }
  // Clear any temporary hover momentary state before toggling
  momentaryHoverLayer = null;
  momentaryHoverTriggerIdx = null;

  const pos = simStack.indexOf(layerIdx);
  if (pos !== -1) {
    simStack.splice(pos, 1);
  } else {
    simStack.push(layerIdx);
    simStack.sort((a, b) => a - b);
  }
  updateLayerTabStates();
  renderSvg();
  triggerRgbFade();
  updateUrlParams();
}

function renderLayerTabs() {
  const kb = KEYBOARDS[currentKb];
  const bar = document.getElementById('layer-tabs');
  bar.innerHTML = '';

  kb.layers.forEach((layer, idx) => {
    const btn = document.createElement('button');
    btn.id = `layer-tab-${idx}`;

    if (viewerMode === 'simulate') {
      const isSimActive = simStack.includes(idx);
      const isMom = (momentaryHoverLayer === idx);
      btn.className = `layer-btn ${isSimActive ? 'sim-active' : ''} ${isMom ? 'sim-momentary' : ''}`;
      btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
      btn.onclick = () => toggleSimLayer(idx);
    } else {
      const isActive = (idx === currentLayer);
      btn.className = `layer-btn ${isActive ? 'active' : ''}`;
      btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
      btn.onclick = () => setLayer(idx);
    }

    bar.appendChild(btn);
  });

  // If in simulate mode and multiple layers active, add reset button to layer bar
  if (viewerMode === 'simulate' && simStack.length > 1) {
    const resetBtn = document.createElement('button');
    resetBtn.id = 'sim-reset-btn';
    resetBtn.className = 'sim-reset-tab-btn';
    resetBtn.innerHTML = '⟲ Reset Stack';
    resetBtn.onclick = resetSimStack;
    bar.appendChild(resetBtn);
  }
}

function updateLayerTabStates() {
  const kb = KEYBOARDS[currentKb];
  const bar = document.getElementById('layer-tabs');
  kb.layers.forEach((layer, idx) => {
    const btn = document.getElementById(`layer-tab-${idx}`);
    if (!btn) return;
    if (viewerMode === 'simulate') {
      const isSimActive = simStack.includes(idx);
      const isMom = (momentaryHoverLayer === idx);
      btn.className = `layer-btn ${isSimActive ? 'sim-active' : ''} ${isMom ? 'sim-momentary' : ''}`;
      btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
    } else {
      const isActive = (idx === currentLayer);
      btn.className = `layer-btn ${isActive ? 'active' : ''}`;
      btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
    }
  });

  const existingReset = document.getElementById('sim-reset-btn');
  if (viewerMode === 'simulate') {
    if (simStack.length > 1 && !existingReset) {
      const resetBtn = document.createElement('button');
      resetBtn.id = 'sim-reset-btn';
      resetBtn.className = 'sim-reset-tab-btn';
      resetBtn.innerHTML = '⟲ Reset Stack';
      resetBtn.onclick = resetSimStack;
      bar.appendChild(resetBtn);
    } else if (simStack.length <= 1 && existingReset) {
      existingReset.remove();
    }
  } else if (existingReset) {
    existingReset.remove();
  }

  const activeTabIdx = (viewerMode === 'simulate' && simStack.length > 0) ? simStack[simStack.length - 1] : currentLayer;
  scrollActiveTabIntoView(activeTabIdx);
}

function scrollActiveTabIntoView(idx) {
  const bar = document.getElementById('layer-tabs');
  const btn = document.getElementById(`layer-tab-${idx}`);
  if (bar && btn) {
    const barRect = bar.getBoundingClientRect();
    const btnRect = btn.getBoundingClientRect();
    if (btnRect.left < barRect.left || btnRect.right > barRect.right) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    }
  }
}

function setLayer(idx, fromKeyLink = false) {
  if (fromKeyLink && idx !== currentLayer) {
    layerHistory.push(currentLayer);
  }
  currentLayer = idx;
  updateBackButton();
  updateLayerTabStates();
  renderSvg();
  triggerRgbFade();
  updateUrlParams();
}

function returnToPreviousLayer() {
  if (layerHistory.length > 0) {
    const prev = layerHistory.pop();
    currentLayer = prev;
    updateBackButton();
    updateLayerTabStates();
    renderSvg();
    triggerRgbFade();
  } else {
    setLayer(0);
  }
  updateUrlParams();
}

function updateBackButton() {
  const btn = document.getElementById('btn-back-layer');
  if (viewerMode === 'inspect' && layerHistory.length > 0) {
    const kb = KEYBOARDS[currentKb];
    const prevIdx = layerHistory[layerHistory.length - 1];
    const prevName = kb.layers[prevIdx] ? kb.layers[prevIdx].name : 'Base';
    btn.innerHTML = `↩ Back to ${prevName} (Esc)`;
    btn.style.display = 'inline-flex';
  } else {
    btn.style.display = 'none';
  }
}

// Crisp vector SVG icon paths (24x24 viewBox, stroke-width 2, rounded caps & joins)
const ICON_PATHS = {
  backspace: `<path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/><line x1="18" y1="9" x2="12" y2="15"/><line x1="12" y1="9" x2="18" y2="15"/>`,
  delete: `<path d="M3 4h13l7 8-7 8H3a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><line x1="7" y1="9" x2="13" y2="15"/><line x1="13" y1="9" x2="7" y2="15"/>`,
  escape: `<path d="M12 12 4.5 4.5"/><polyline points="11 4.5 4.5 4.5 4.5 11"/><path d="M7 16A7.5 7.5 0 1 0 16 7"/>`,
  tab: `<path d="M4 12h12"/><polyline points="11 7 16 12 11 17"/><line x1="20" y1="5" x2="20" y2="19"/>`,
  enter: `<polyline points="9 10 4 15 9 20"/><path d="M20 5v6a4 4 0 0 1-4 4H4"/>`,
  space: `<path d="M5 9v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9"/>`,
  caps: `<path d="M12 4 5.5 10.5h3.5v5h6v-5h3.5z"/><line x1="5.5" y1="19" x2="18.5" y2="19"/>`,
  vol_up: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a9 9 0 0 1 0 14"/>`,
  vol_down: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>`,
  mute: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="22" y1="9" x2="16" y2="15"/><line x1="16" y1="9" x2="22" y2="15"/>`,
  bri_up: `<circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/>`,
  bri_down: `<circle cx="12" cy="12" r="3"/><line x1="12" y1="4" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="20"/><line x1="4" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="20" y2="12"/>`,
  prtsc: `<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>`,
  screenshot: `<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>`,
  rocket: `<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>`,
  clipboard: `<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>`,
  ins: `<rect x="4" y="4" width="16" height="16" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>`
};

const FRIENDLY_NAMES = {
  backspace: '⌫ Bksp',
  escape: '⎋ Esc',
  tab: '⇥ Tab',
  enter: '↵ Enter',
  delete: '⌦ Del',
  space: '␣ Space',
  caps: '⇪ Caps',
  vol_up: '🔊 Vol +',
  vol_down: '🔉 Vol -',
  mute: '🔇 Mute',
  bri_up: '🔆 Bri +',
  bri_down: '🔅 Bri -',
  prtsc: '📷 PrtSc',
  screenshot: '📷 Screenshot',
  rocket: '🚀 Launcher',
  clipboard: '📋 Clipboard',
  ins: 'Ins'
};

const ICON_SEARCH_ALIASES = {
  backspace: ['backspace', 'bksp', 'bspc', 'del', 'erase'],
  escape: ['escape', 'esc'],
  tab: ['tab', 'tabulator'],
  enter: ['enter', 'return', 'ret'],
  delete: ['delete', 'del', 'forward delete'],
  space: ['space', 'spacebar'],
  caps: ['caps', 'capslock', 'caps lock', 'capital'],
  vol_up: ['vol', 'volume', 'louder'],
  vol_down: ['vol', 'volume', 'quieter'],
  mute: ['mute', 'silence', 'audio'],
  bri_up: ['bri', 'brightness', 'light'],
  bri_down: ['bri', 'brightness', 'dim'],
  prtsc: ['prtsc', 'print', 'screen', 'screenshot', 'capture'],
  screenshot: ['screenshot', 'screen capture', 'snap', 'capture', 'cleanshot', 'prtsc'],
  rocket: ['launcher', 'launch', 'rocket', 'gemini', 'spotlight', 'raycast', 'alfred', 'space', 'cmd space'],
  clipboard: ['clipboard', 'copy', 'paste', 'clip', 'c/v', 'copy paste'],
  ins: ['ins', 'insert']
};

function getInspectorLabel(key) {
  if (!key) return '—';
  if (key.icon && FRIENDLY_NAMES[key.icon]) {
    return FRIENDLY_NAMES[key.icon];
  }
  return key.line2 ? `${key.line1} ${key.line2}` : (key.line1 || '—');
}

function renderKeyPrimary(key, cx, cy, primaryFontSize, primaryFontWeight) {
  // 1. Single action key with dedicated vector icon
  if (key.icon && ICON_PATHS[key.icon] && !key.line2) {
    const size = 20;
    const half = size / 2;
    // Shift slightly down if secondary label exists in top-right corner
    const offsetY = key.secondary ? 2.5 : 0;
    const ix = cx - half;
    const iy = cy + offsetY - half;

    return `
      <svg class="key-icon icon-${key.icon}" x="${ix}" y="${iy}" width="${size}" height="${size}"
           viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        ${ICON_PATHS[key.icon]}
      </svg>
    `;
  }

  // 2. Generic 2-line label
  if (key.line2) {
    return `
      <text class="key-text-primary" x="${cx}" y="${cy - 5.5}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line1)}</text>
      <text class="key-text-primary" x="${cx}" y="${cy + 7.5}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line2)}</text>
    `;
  }

  // 3. Generic 1-line label
  return `
    <text class="key-text-primary" x="${cx}" y="${cy + (key.secondary ? 2.5 : 0)}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line1)}</text>
  `;
}

function renderSvg() {
  const kb = KEYBOARDS[currentKb];
  const coords = kb.coords;
  const layer = kb.layers[currentLayer];
  const baseLayer = kb.layers[0];
  const svg = document.getElementById('keyboard-svg');

  if (svg) {
    svg.setAttribute('viewBox', currentKb === 'glove80' ? '-15 -10 1000 460' : '-15 -10 970 365');
  }

  let html = '';

  coords.forEach((c, idx) => {
    let key;
    let isPassThrough = false;
    let sourceLayer = currentLayer;

    if (viewerMode === 'simulate') {
      const resKey = resolveCompositeKey(idx);
      const resRgb = resolveCompositeRgb(idx);
      key = {
        ...resKey.key,
        rgbHex: resRgb.rgbHex,
        rgbToken: resRgb.rgbToken
      };
      sourceLayer = resKey.sourceLayer;
    } else {
      const rawKey = layer.keys[idx] || { line1: '', line2: '', secondary: '', badge: '', rgbHex: '#000000', rawBinding: '' };
      const isTrans = (rawKey.line1 === '▽' || rawKey.rawBinding === '&trans');
      key = rawKey;

      if (isTrans && currentLayer !== 0 && baseLayer && baseLayer.keys[idx]) {
        const baseK = baseLayer.keys[idx];
        if (baseK && baseK.line1 !== '▽' && baseK.rawBinding !== '&trans') {
          isPassThrough = true;
          key = {
            ...rawKey,
            line1: baseK.line1,
            line2: baseK.line2,
            secondary: baseK.secondary,
            badge: '',
            icon: baseK.icon,
            tooltip: `Pass-through (Inherited from Base: ${baseK.tooltip || baseK.line1})`,
            rawBinding: `&trans (Inherits Base: ${baseK.rawBinding})`
          };
        }
      }
    }

    const x = c.x * UNIT;
    const y = c.y * UNIT;
    const r = c.r || 0;
    const cx = x + KEY_SIZE / 2;
    const cy = y + KEY_SIZE / 2;

    let pivotX = (c.rx !== undefined) ? c.rx * UNIT : x;
    let pivotY = (c.ry !== undefined) ? c.ry * UNIT : y;

    const isMatched = searchQuery && (
      (key.line1 && key.line1.toLowerCase().includes(searchQuery)) ||
      (key.line2 && key.line2.toLowerCase().includes(searchQuery)) ||
      (key.secondary && key.secondary.toLowerCase().includes(searchQuery)) ||
      (key.rawBinding && key.rawBinding.toLowerCase().includes(searchQuery)) ||
      (key.tooltip && key.tooltip.toLowerCase().includes(searchQuery)) ||
      (key.icon && (key.icon.toLowerCase().includes(searchQuery) || (ICON_SEARCH_ALIASES[key.icon] && ICON_SEARCH_ALIASES[key.icon].some(alias => alias.includes(searchQuery)))))
    );

    let capClass = 'key-cap';
    if (isPassThrough) {
      capClass += ' pass-through';
    } else if (key.line1 === '▽') {
      capClass += ' trans';
    } else if (key.line1 === '—') {
      capClass += ' none';
    }

    const hasLayerLink = key.targetLayer !== null && key.targetLayer !== undefined;
    const rotAttr = r ? `transform="rotate(${r} ${pivotX} ${pivotY})"` : '';
    const groupClass = `key-group ${isMatched ? 'matched' : ''} ${hasLayerLink ? 'has-layer-link' : ''} ${isPassThrough ? 'is-pass-through' : ''}`;

    let primaryFontSize = 13.5;
    let primaryFontWeight = 700;
    if (key.line2) {
      primaryFontSize = key.line1.length > 5 ? 8.5 : 9.5;
    } else if (key.line1.length > 6) {
      primaryFontSize = 9;
      primaryFontWeight = 600;
    } else if (key.line1.length > 3) {
      primaryFontSize = 11;
    }

    const secFontSize = (key.secondary && key.secondary.length > 5) ? '7.8px' : '9px';

    html += `
      <g class="${groupClass}" ${rotAttr}
         onclick="onKeyClick(${idx})"
         onmouseenter="onKeyHover(${idx})"
         data-idx="${idx}">

        <!-- RGB Glow border -->
        <rect class="key-glow" x="${x-2}" y="${y-2}" width="${KEY_SIZE+4}" height="${KEY_SIZE+4}" stroke="${key.rgbHex}" />

        <!-- Tactile Keycap -->
        <rect class="${capClass}" x="${x}" y="${y}" width="${KEY_SIZE}" height="${KEY_SIZE}" />

        <!-- Pass-through watermark icon -->
        ${isPassThrough ? `<text class="trans-watermark" x="${x + 4}" y="${y + 10}">▽</text>` : ''}

        <!-- Corner Secondary / Mod / Layer Name -->
        ${key.secondary ? `
          <text class="${hasLayerLink ? 'key-text-layer-link' : 'key-text-sec'}"
                x="${x + KEY_SIZE - 4}" y="${y + 4.5}"
                font-size="${secFontSize}">${escapeHtml(key.secondary)}</text>
        ` : ''}

        <!-- Badge (Top-Left) -->
        ${key.badge ? `
          <text class="key-badge badge-${key.badgeType}" x="${x + 5}" y="${y + 4.5}">${escapeHtml(key.badge)}</text>
        ` : ''}

        <!-- Primary Label (Centered Icon or Text) -->
        ${renderKeyPrimary(key, cx, cy, primaryFontSize, primaryFontWeight)}
      </g>
    `;
  });

  svg.innerHTML = html;
}

function onKeyClick(idx) {
  if (isTouchDragging) return;
  const kb = KEYBOARDS[currentKb];

  if (viewerMode === 'inspect') {
    const key = kb.layers[currentLayer].keys[idx];
    if (key && key.targetLayer !== null && key.targetLayer !== undefined && key.targetLayer !== currentLayer) {
      setLayer(key.targetLayer, true);
      return;
    }
    inspectKey(idx);
  } else {
    // In Simulation Mode:
    // If clicking the key that triggered a momentary hover preview, clear the temporary hover state
    // so toggleSimLayer cleanly manages the permanent simStack
    if (momentaryHoverTriggerIdx === idx) {
      momentaryHoverLayer = null;
      momentaryHoverTriggerIdx = null;
    }

    const { key } = resolveCompositeKey(idx);

    // Explicit &to switch (e.g. &to 7 Factory layer)
    if (key.rawBinding && /^&to\s/.test(key.rawBinding) && key.targetLayer !== null) {
      simStack = key.targetLayer === 0 ? [0] : [0, key.targetLayer];
      momentaryHoverLayer = null;
      momentaryHoverTriggerIdx = null;
      updateLayerTabStates();
      renderSvg();
      triggerRgbFade();
      inspectKey(idx);
      updateUrlParams();
      return;
    }

    if (key.targetLayer !== null && key.targetLayer !== undefined) {
      toggleSimLayer(key.targetLayer);
      inspectKey(idx);
      return;
    }

    inspectKey(idx);
  }
}

function onKeyHover(idx) {
  if (isTouchDragging) return;
  // In ALL modes: desktop hover immediately updates the footer info drawer!
  inspectKey(idx);

  // In Simulation Mode: hovering over a momentary layer key triggers it live!
  if (viewerMode === 'simulate') {
    const { key } = resolveCompositeKey(idx);
    if (key && key.targetLayer !== null && key.targetLayer !== undefined && !key.rawBinding.startsWith('&tog') && !key.rawBinding.startsWith('&to')) {
      activateHoverMomentary(idx, key.targetLayer);
    }
  }
}

function inspectKey(idx) {
  const kb = KEYBOARDS[currentKb];
  const coord = kb.coords[idx];
  if (!coord) return;

  let key, displayLayerName, rgbHex, rgbToken, rgbSource;

  if (viewerMode === 'simulate') {
    const res = resolveCompositeKey(idx);
    key = res.key;
    const srcLayer = res.sourceLayer;
    displayLayerName = `${srcLayer}: ${kb.layers[srcLayer] ? kb.layers[srcLayer].name : 'Base'}`;

    const rgbRes = resolveCompositeRgb(idx);
    rgbHex = rgbRes.rgbHex;
    rgbToken = rgbRes.rgbToken;
    rgbSource = (rgbRes.rgbSourceLayer !== null) ? `(${kb.layers[rgbRes.rgbSourceLayer].name})` : '';
  } else {
    const layer = kb.layers[currentLayer];
    key = layer.keys[idx];
    displayLayerName = `${currentLayer}: ${layer.name}`;
    rgbHex = key.rgbHex;
    rgbToken = key.rgbToken;
    rgbSource = '';
  }

  const fullLabel = getInspectorLabel(key);
  document.getElementById('insp-label').textContent = fullLabel;

  const titleEl = document.getElementById('insp-title');
  const detailEl = document.getElementById('insp-detail');

  let rgbDesc = (rgbToken && rgbToken !== '___')
    ? `RGB: <span style="color:${rgbHex}; font-weight:700;">${rgbToken}</span> ${rgbSource}`
    : 'RGB: Unlit';

  let layerJumpHtml = '';
  if (viewerMode === 'inspect' && key.targetLayer !== null && key.targetLayer !== undefined) {
    const targetName = kb.layers[key.targetLayer] ? kb.layers[key.targetLayer].name : `Layer ${key.targetLayer}`;
    layerJumpHtml = `<button class="jump-layer-btn" onclick="setLayer(${key.targetLayer}, true)">Go to ${targetName} →</button>`;
  }

  const isMobile = window.innerWidth <= 768;
  const layerLabel = (viewerMode === 'simulate' && !isMobile) ? 'Active Source Layer' : 'Layer';

  titleEl.innerHTML = `<strong>${coord.label}</strong> (Key #${idx}) • ${layerLabel}: <strong>${displayLayerName}</strong> • ${rgbDesc} ${layerJumpHtml}`;
  detailEl.innerHTML = `ZMK: <code style="color:var(--accent); background:#090d12; padding:2px 6px; border-radius:4px;">${escapeHtml(key.rawBinding)}</code> • ${escapeHtml(key.tooltip)}`;

  const rgbText = (rgbToken && rgbToken !== '___') ? `RGB: ${rgbToken} ${rgbSource}` : 'RGB: Unlit';
  titleEl.title = `${coord.label} (Key #${idx}) • ${layerLabel}: ${displayLayerName} • ${rgbText}`;
  detailEl.title = `ZMK: ${key.rawBinding} • ${key.tooltip}`;
}

function resetInspector() {
  document.getElementById('insp-label').textContent = '—';
  const titleEl = document.getElementById('insp-title');
  const detailEl = document.getElementById('insp-detail');
  const isMobile = window.innerWidth <= 768;
  if (viewerMode === 'simulate') {
    titleEl.textContent = isMobile
      ? 'Simulation Mode: Tap momentary layer keys to activate'
      : 'Simulation Mode: Hover momentary layer keys to activate • Click to lock/toggle';
    detailEl.textContent = isMobile
      ? 'Tap any key to inspect • Tap top buttons to switch layers'
      : 'Shortcuts: [0-9] Toggle Layer • [M] Switch to Inspect • [C] Color Guide • [Esc] Reset Stack';
  } else {
    titleEl.textContent = isMobile
      ? 'Inspect Mode: Tap any key to inspect details'
      : 'Inspect Mode: Click any key to inspect details or navigate layers';
    detailEl.textContent = isMobile
      ? 'Tap any key to inspect • Tap top buttons to switch layers'
      : 'Shortcuts: [0-9] Layer • [M] Switch to Simulate • [R] Toggle RGB • [C] Color Guide • [Esc] Back';
  }
  titleEl.title = '';
  detailEl.title = '';
}

function handleSearch(val) {
  searchQuery = val.trim().toLowerCase();
  renderSvg();
}

function applyTransform(animated = false) {
  const svg = document.getElementById('keyboard-svg');
  const container = document.getElementById('viewport-container') || document.querySelector('.viewport-container');
  if (!svg) return;

  svg.style.transition = animated ? 'transform 0.22s cubic-bezier(0.2, 0.9, 0.3, 1)' : 'none';
  svg.style.transform = `translate(${currentPanX}px, ${currentPanY}px) scale(${currentScale})`;

  if (container) {
    container.classList.toggle('is-zoomed', currentScale > 1.05);
  }
}

function clampPan(animated = false) {
  const container = document.getElementById('viewport-container') || document.querySelector('.viewport-container');
  if (!container) return;

  if (currentScale <= 1.0) {
    currentPanX = 0;
    currentPanY = 0;
    if (currentScale < MIN_SCALE) {
      currentScale = MIN_SCALE;
    }
    applyTransform(animated);
    return;
  }

  const rect = container.getBoundingClientRect();
  const maxPanX = Math.max(60, (rect.width * (currentScale - 0.7)) / 2 + 80);
  const maxPanY = Math.max(50, (rect.height * (currentScale - 0.7)) / 2 + 60);

  currentPanX = Math.min(maxPanX, Math.max(-maxPanX, currentPanX));
  currentPanY = Math.min(maxPanY, Math.max(-maxPanY, currentPanY));

  applyTransform(animated);
}

function zoom(factor) {
  currentScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, currentScale * factor));
  if (Math.abs(currentScale - 1.0) < 0.03) {
    currentScale = 1.0;
    currentPanX = 0;
    currentPanY = 0;
  } else if (currentScale < 1.0) {
    currentPanX = 0;
    currentPanY = 0;
  } else {
    clampPan(false);
  }
  applyTransform(true);
}

function resetZoom() {
  currentScale = 1.0;
  currentPanX = 0;
  currentPanY = 0;
  applyTransform(true);
}

function initCanvasGestures() {
  const container = document.getElementById('viewport-container') || document.querySelector('.viewport-container');
  if (!container) return;

  // Touch tracking state
  let touchMode = 'none'; // 'none' | 'pan' | 'pinch'
  let touchStartX = 0;
  let touchStartY = 0;
  let touchStartPanX = 0;
  let touchStartPanY = 0;
  let touchMoved = false;
  let touchDragTimer = null;

  let pinchInitialDist = 0;
  let pinchInitialScale = 1.0;
  let pinchInitialPanX = 0;
  let pinchInitialPanY = 0;
  let pinchInitialFocal = { x: 0, y: 0 };

  container.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1) {
      touchMode = 'pan';
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      touchStartPanX = currentPanX;
      touchStartPanY = currentPanY;
      touchMoved = false;
    } else if (e.touches.length === 2) {
      touchMode = 'pinch';
      touchMoved = true;
      isTouchDragging = true;
      if (touchDragTimer) clearTimeout(touchDragTimer);

      pinchInitialDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      pinchInitialScale = currentScale;
      pinchInitialPanX = currentPanX;
      pinchInitialPanY = currentPanY;
      pinchInitialFocal = {
        x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
        y: (e.touches[0].clientY + e.touches[1].clientY) / 2
      };
      if (e.cancelable) e.preventDefault();
    }
  }, { passive: false });

  container.addEventListener('touchmove', (e) => {
    if (touchMode === 'pinch' && e.touches.length === 2) {
      if (e.cancelable) e.preventDefault();
      touchMoved = true;
      isTouchDragging = true;

      const currentDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      if (pinchInitialDist <= 0) return;

      const scaleFactor = currentDist / pinchInitialDist;
      const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, pinchInitialScale * scaleFactor));
      currentScale = newScale;

      const currentFocal = {
        x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
        y: (e.touches[0].clientY + e.touches[1].clientY) / 2
      };

      const rect = container.getBoundingClientRect();
      const focalRelX = pinchInitialFocal.x - (rect.left + rect.width / 2);
      const focalRelY = pinchInitialFocal.y - (rect.top + rect.height / 2);
      const scaleRatio = newScale / pinchInitialScale;

      currentPanX = pinchInitialPanX + (currentFocal.x - pinchInitialFocal.x) + (1 - scaleRatio) * focalRelX;
      currentPanY = pinchInitialPanY + (currentFocal.y - pinchInitialFocal.y) + (1 - scaleRatio) * focalRelY;

      applyTransform(false);
    } else if (touchMode === 'pan' && e.touches.length === 1) {
      const dx = e.touches[0].clientX - touchStartX;
      const dy = e.touches[0].clientY - touchStartY;
      const dist = Math.hypot(dx, dy);

      if (!touchMoved && dist > 7) {
        touchMoved = true;
        isTouchDragging = true;
        if (touchDragTimer) clearTimeout(touchDragTimer);
      }

      if (touchMoved) {
        if (e.cancelable) e.preventDefault();
        currentPanX = touchStartPanX + dx;
        currentPanY = touchStartPanY + dy;
        applyTransform(false);
      }
    }
  }, { passive: false });

  const endTouch = (e) => {
    if (e.touches.length === 0) {
      if (touchMoved) {
        isTouchDragging = true;
        if (touchDragTimer) clearTimeout(touchDragTimer);
        touchDragTimer = setTimeout(() => {
          isTouchDragging = false;
        }, 150);
        clampPan(true);
      }
      touchMode = 'none';
      touchMoved = false;
    } else if (e.touches.length === 1) {
      touchMode = 'pan';
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      touchStartPanX = currentPanX;
      touchStartPanY = currentPanY;
      touchMoved = false;
    }
  };

  container.addEventListener('touchend', endTouch);
  container.addEventListener('touchcancel', endTouch);

  // Desktop Trackpad Pinch-to-zoom & Pan / Wheel support
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - (rect.left + rect.width / 2);
    const mouseY = e.clientY - (rect.top + rect.height / 2);

    if (e.ctrlKey) {
      // Trackpad pinch-to-zoom or Ctrl+Wheel
      const factor = Math.exp(-e.deltaY * 0.01);
      const newScale = Math.min(MAX_SCALE, Math.max(1.0, currentScale * factor));
      if (newScale !== currentScale) {
        const scaleRatio = newScale / currentScale;
        currentScale = newScale;
        if (currentScale > 1.0) {
          currentPanX = currentPanX + (1 - scaleRatio) * (mouseX - currentPanX);
          currentPanY = currentPanY + (1 - scaleRatio) * (mouseY - currentPanY);
          clampPan(false);
        } else {
          currentScale = 1.0;
          currentPanX = 0;
          currentPanY = 0;
        }
        applyTransform(false);
      }
    } else if (currentScale > 1.0) {
      // Two-finger scroll on trackpad or mouse wheel pan when zoomed in
      currentPanX -= e.deltaX;
      currentPanY -= e.deltaY;
      clampPan(false);
      applyTransform(false);
    }
  }, { passive: false });

  // Desktop Mouse Drag to pan when zoomed in
  let isMouseDown = false;
  let mouseStartX = 0;
  let mouseStartY = 0;
  let mouseStartPanX = 0;
  let mouseStartPanY = 0;
  let mouseMoved = false;

  container.addEventListener('mousedown', (e) => {
    if (e.button === 0 || e.button === 1) {
      if (currentScale > 1.0 || e.button === 1) {
        isMouseDown = true;
        mouseStartX = e.clientX;
        mouseStartY = e.clientY;
        mouseStartPanX = currentPanX;
        mouseStartPanY = currentPanY;
        mouseMoved = false;
      }
    }
  });

  window.addEventListener('mousemove', (e) => {
    if (!isMouseDown) return;
    const dx = e.clientX - mouseStartX;
    const dy = e.clientY - mouseStartY;
    if (!mouseMoved && Math.hypot(dx, dy) > 5) {
      mouseMoved = true;
      isTouchDragging = true;
      container.classList.add('is-panning');
    }
    if (mouseMoved) {
      currentPanX = mouseStartPanX + dx;
      currentPanY = mouseStartPanY + dy;
      applyTransform(false);
    }
  });

  window.addEventListener('mouseup', () => {
    if (isMouseDown) {
      isMouseDown = false;
      container.classList.remove('is-panning');
      if (mouseMoved) {
        if (touchDragTimer) clearTimeout(touchDragTimer);
        touchDragTimer = setTimeout(() => {
          isTouchDragging = false;
        }, 150);
        clampPan(true);
      }
    }
  });

  window.addEventListener('resize', () => {
    if (currentScale > 1.0) {
      clampPan(false);
    }
    const labelEl = document.getElementById('insp-label');
    if (labelEl && labelEl.textContent === '—') {
      resetInspector();
    }
  });
}

let drawerCollapsed = false;

function toggleDrawer(forceState) {
  const drawer = document.getElementById('main-drawer');
  if (!drawer) return;
  if (typeof forceState === 'boolean') {
    drawerCollapsed = forceState;
  } else {
    drawerCollapsed = !drawerCollapsed;
  }
  drawer.classList.toggle('collapsed', drawerCollapsed);
  const btn = document.getElementById('btn-drawer-toggle');
  if (btn) {
    btn.title = drawerCollapsed ? 'Expand Key Inspector (I)' : 'Collapse Key Inspector (I)';
  }
}

let canvasWidgetCollapsed = false;

function toggleCanvasWidget(forceState) {
  const widget = document.getElementById('canvas-widget');
  if (!widget) return;
  if (typeof forceState === 'boolean') {
    canvasWidgetCollapsed = forceState;
  } else {
    canvasWidgetCollapsed = !canvasWidgetCollapsed;
  }
  widget.classList.toggle('collapsed', canvasWidgetCollapsed);
  const btn = document.getElementById('btn-widget-toggle');
  if (btn) {
    btn.title = canvasWidgetCollapsed ? 'Expand Canvas Tools (T)' : 'Collapse Canvas Tools (T)';
  }
}

function toggleZenMode() {
  document.body.classList.toggle('zen-mode');
  const isZen = document.body.classList.contains('zen-mode');
  const btn = document.getElementById('btn-zen');
  if (btn) {
    btn.classList.toggle('active', isZen);
    btn.title = isZen ? 'Exit Full View (Esc or F)' : 'Focus / Full View (F)';
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
