const KEYBOARDS = JSON.parse(document.getElementById('embedded-data').textContent);
let currentKb = 'glove80';
let currentLayer = 0;
let viewerMode = 'simulate'; // Default mode is Simulate
let simStack = [0]; // Active layer indices in simulation mode
let momentaryHoverLayer = null;
let momentaryHoverTriggerIdx = null;
let rgbFadeTimer = null;
let layerHistory = [];
let rgbEnabled = true;
let selectedKeyIdx = null;
let currentScale = 1.0;
let searchQuery = '';

const UNIT = 54;
const KEY_SIZE = 48;

function readUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const kbParam = params.get('kb');
  if (kbParam && KEYBOARDS[kbParam.toLowerCase()]) {
    currentKb = kbParam.toLowerCase();
  }
  const modeParam = params.get('mode');
  if (modeParam && ['simulate', 'inspect'].includes(modeParam.toLowerCase())) {
    viewerMode = modeParam.toLowerCase();
  }
  const layerParam = params.get('layer');
  if (layerParam !== null && layerParam !== '') {
    const kb = KEYBOARDS[currentKb];
    if (viewerMode === 'inspect') {
      const idx = parseInt(layerParam, 10);
      if (!isNaN(idx) && idx >= 0 && idx < kb.layers.length) {
        currentLayer = idx;
      }
    } else {
      const indices = layerParam.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n >= 0 && n < kb.layers.length);
      if (indices.length > 0) {
        simStack = Array.from(new Set([0, ...indices])).sort((a, b) => a - b);
      }
    }
  }
}

function updateUrlParams() {
  const params = new URLSearchParams();
  params.set('kb', currentKb);
  params.set('mode', viewerMode);
  if (viewerMode === 'inspect') {
    if (currentLayer !== 0) {
      params.set('layer', currentLayer);
    }
  } else {
    const activeLayers = simStack.filter(idx => idx !== 0);
    if (activeLayers.length > 0) {
      params.set('layer', activeLayers.join(','));
    }
  }
  const qs = params.toString();
  const newUrl = window.location.pathname + (qs ? '?' + qs : '');
  window.history.replaceState(null, '', newUrl);
}

function init() {
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
        selectedKeyIdx = null;
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

function triggerRgbFade() {
  if (!rgbEnabled) return;
  const svg = document.getElementById('keyboard-svg');
  if (!svg) return;

  if (viewerMode === 'simulate') {
    svg.classList.remove('rgb-faded'); // Light up immediately on layer change

    if (rgbFadeTimer) {
      clearTimeout(rgbFadeTimer);
    }

    // Fade out after exactly 1 second (1000ms)
    rgbFadeTimer = setTimeout(() => {
      if (viewerMode === 'simulate') {
        svg.classList.add('rgb-faded');
      }
    }, 1000);
  } else {
    if (rgbFadeTimer) clearTimeout(rgbFadeTimer);
    svg.classList.remove('rgb-faded');
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
  selectedKeyIdx = null;
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
  selectedKeyIdx = null;
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
  document.getElementById('kb-version').textContent = match ? match[0] : 'v27';
}

function toggleRgb() {
  rgbEnabled = !rgbEnabled;
  const btn = document.getElementById('btn-rgb');
  const svg = document.getElementById('keyboard-svg');
  if (btn) {
    btn.textContent = `RGB: ${rgbEnabled ? 'ON' : 'OFF'}`;
    btn.classList.toggle('active', rgbEnabled);
  }
  if (svg) {
    svg.classList.toggle('rgb-mode', rgbEnabled);
  }
  if (rgbEnabled) triggerRgbFade();
}

function getActiveSimLayers() {
  if (momentaryHoverLayer !== null && !simStack.includes(momentaryHoverLayer)) {
    const list = [...simStack, momentaryHoverLayer];
    list.sort((a, b) => a - b);
    return list;
  }
  return simStack;
}

function resolveCompositeKey(idx) {
  const kb = KEYBOARDS[currentKb];
  const activeLayers = getActiveSimLayers();
  for (let i = activeLayers.length - 1; i >= 0; i--) {
    const layerIdx = activeLayers[i];
    const key = kb.layers[layerIdx] && kb.layers[layerIdx].keys[idx];
    if (key && key.rawBinding !== '&trans' && key.line1 !== '▽') {
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
  if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
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
  if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
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
}

function setLayer(idx, fromKeyLink = false) {
  if (fromKeyLink && idx !== currentLayer) {
    layerHistory.push(currentLayer);
  }
  currentLayer = idx;
  updateBackButton();
  updateLayerTabStates();
  renderSvg();
  if (selectedKeyIdx !== null) {
    inspectKey(selectedKeyIdx);
  }
  updateUrlParams();
}

function returnToPreviousLayer() {
  if (layerHistory.length > 0) {
    const prev = layerHistory.pop();
    currentLayer = prev;
    updateBackButton();
    updateLayerTabStates();
    renderSvg();
    if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
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

  if (currentKb === 'glove80') {
    svg.setAttribute('viewBox', '-15 -10 1000 460');
  } else {
    svg.setAttribute('viewBox', '-15 -10 970 365');
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

    const isSelected = selectedKeyIdx === idx;
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
    const groupClass = `key-group ${isSelected ? 'selected' : ''} ${isMatched ? 'matched' : ''} ${hasLayerLink ? 'has-layer-link' : ''} ${isPassThrough ? 'is-pass-through' : ''}`;

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
    selectedKeyIdx = idx;
    renderSvg();
    inspectKey(idx);
  } else {
    // In Simulation Mode:
    const { key } = resolveCompositeKey(idx);

    if (key.rawBinding && key.rawBinding.startsWith('&to') && key.targetLayer !== null) {
      simStack = [key.targetLayer];
      momentaryHoverLayer = null;
      momentaryHoverTriggerIdx = null;
      updateLayerTabStates();
      renderSvg();
      triggerRgbFade();
      selectedKeyIdx = idx;
      inspectKey(idx);
      updateUrlParams();
      return;
    }

    if (key.targetLayer !== null && key.targetLayer !== undefined) {
      toggleSimLayer(key.targetLayer);
      selectedKeyIdx = idx;
      inspectKey(idx);
      return;
    }

    selectedKeyIdx = idx;
    renderSvg();
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
}

function resetInspector() {
  document.getElementById('insp-label').textContent = '—';
  if (viewerMode === 'simulate') {
    document.getElementById('insp-title').textContent = 'Simulation Mode: Hover momentary layer keys to activate • Click to lock/toggle';
    document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Toggle Layer • [M] Switch to Inspect • [C] Color Guide • [Esc] Reset Stack';
  } else {
    document.getElementById('insp-title').textContent = 'Inspect Mode: Click any key to inspect details or navigate layers';
    document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Layer • [M] Switch to Simulate • [C] Color Guide • [Esc] Back';
  }
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

window.onload = init;
