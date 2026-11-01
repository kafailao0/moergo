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
}

function updateUrlParams() {
  const params = new URLSearchParams();
  params.set('kb', currentKb);
  params.set('mode', viewerMode);
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
  updateHeader();
  resetInspector();
  triggerRgbFade();
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
    } else if (e.key === '/') {
      e.preventDefault();
      document.getElementById('search-input').focus();
    } else if (e.key === 'Escape') {
      if (viewerMode === 'simulate') {
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
  const match = kb.title.match(/v[0-9]+/);
  document.getElementById('kb-version').textContent = match ? match[0] : 'v28';
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
      btn.innerHTML = `${isSimActive ? '<span class="sim-check-icon">✓</span>' : ''}<span class="idx">${idx}</span> ${layer.name}`;
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
      btn.innerHTML = `${isSimActive ? '<span class="sim-check-icon">✓</span>' : ''}<span class="idx">${idx}</span> ${layer.name}`;
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
  updateUrlParams();
}

function returnToPreviousLayer() {
  if (layerHistory.length > 0) {
    const prev = layerHistory.pop();
    currentLayer = prev;
    updateBackButton();
    updateLayerTabStates();
    renderSvg();
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
      (key.tooltip && key.tooltip.toLowerCase().includes(searchQuery))
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

        <!-- Primary Label (Centered, 1 or 2 lines) -->
        ${key.line2 ? `
          <text class="key-text-primary" x="${cx}" y="${cy - 5.5}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line1)}</text>
          <text class="key-text-primary" x="${cx}" y="${cy + 7.5}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line2)}</text>
        ` : `
          <text class="key-text-primary" x="${cx}" y="${cy + (key.secondary ? 2.5 : 0)}" font-size="${primaryFontSize}" font-weight="${primaryFontWeight}">${escapeHtml(key.line1)}</text>
        `}
      </g>
    `;
  });

  svg.innerHTML = html;
}

function onKeyClick(idx) {
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

  const fullLabel = key.line2 ? `${key.line1} ${key.line2}` : (key.line1 || '—');
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

  titleEl.innerHTML = `<strong>${coord.label}</strong> (Key #${idx}) • ${viewerMode === 'simulate' ? 'Active Source Layer' : 'Layer'}: <strong>${displayLayerName}</strong> • ${rgbDesc} ${layerJumpHtml}`;
  detailEl.innerHTML = `ZMK: <code style="color:var(--accent); background:#090d12; padding:2px 6px; border-radius:4px;">${escapeHtml(key.rawBinding)}</code> • ${escapeHtml(key.tooltip)}`;

  const rgbText = (rgbToken && rgbToken !== '___') ? `RGB: ${rgbToken} ${rgbSource}` : 'RGB: Unlit';
  titleEl.title = `${coord.label} (Key #${idx}) • ${viewerMode === 'simulate' ? 'Active Source Layer' : 'Layer'}: ${displayLayerName} • ${rgbText}`;
  detailEl.title = `ZMK: ${key.rawBinding} • ${key.tooltip}`;
}

function resetInspector() {
  document.getElementById('insp-label').textContent = '—';
  const titleEl = document.getElementById('insp-title');
  const detailEl = document.getElementById('insp-detail');
  if (viewerMode === 'simulate') {
    titleEl.textContent = 'Simulation Mode: Hover momentary layer keys to activate • Click to lock/toggle';
    detailEl.textContent = 'Shortcuts: [0-9] Toggle Layer • [M] Switch to Inspect • [C] Color Guide • [Esc] Reset Stack';
  } else {
    titleEl.textContent = 'Inspect Mode: Click any key to inspect details or navigate layers';
    detailEl.textContent = 'Shortcuts: [0-9] Layer • [M] Switch to Simulate • [R] Toggle RGB • [C] Color Guide • [Esc] Back';
  }
  titleEl.title = '';
  detailEl.title = '';
}

function handleSearch(val) {
  searchQuery = val.trim().toLowerCase();
  renderSvg();
}

function zoom(factor) {
  currentScale *= factor;
  const svg = document.getElementById('keyboard-svg');
  svg.style.transform = `scale(${currentScale})`;
}

function resetZoom() {
  currentScale = 1.0;
  const svg = document.getElementById('keyboard-svg');
  svg.style.transform = 'scale(1)';
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
