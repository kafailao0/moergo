const KEYBOARDS = JSON.parse(document.getElementById('embedded-data').textContent);
let currentKb = 'glove80';
let currentLayer = 0;
let viewerMode = 'inspect'; // 'inspect' | 'simulate'
let simStack = [0]; // Active layer indices in simulation mode
let momentaryHeldLayer = null;
let layerHistory = [];
let rgbEnabled = true;
let selectedKeyIdx = null;
let currentScale = 1.0;
let searchQuery = '';

const UNIT = 54;
const KEY_SIZE = 48;

function init() {
  renderLayerTabs();
  renderSvg();
  updateHeader();
  resetInspector();

  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') {
      if (e.key === 'Escape') {
        e.target.blur();
        e.target.value = '';
        handleSearch('');
      }
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

  // Global pointerup to release momentary held layers in simulation mode
  document.addEventListener('pointerup', () => {
    if (viewerMode === 'simulate' && momentaryHeldLayer !== null) {
      const pos = simStack.indexOf(momentaryHeldLayer);
      if (pos !== -1) {
        simStack.splice(pos, 1);
      }
      momentaryHeldLayer = null;
      updateSimBanner();
      updateLayerTabStates();
      renderSvg();
    }
  });
}

function setViewerMode(mode) {
  if (viewerMode === mode) return;
  viewerMode = mode;
  document.getElementById('btn-mode-inspect').classList.toggle('active', mode === 'inspect');
  document.getElementById('btn-mode-sim').classList.toggle('active', mode === 'simulate');

  const simBanner = document.getElementById('sim-banner');
  const previewBanner = document.getElementById('preview-banner');
  const backBtn = document.getElementById('btn-back-layer');

  if (mode === 'simulate') {
    previewBanner.style.display = 'none';
    simBanner.style.display = 'inline-flex';
    backBtn.style.display = 'none';
    if (!simStack.includes(0)) simStack = [0];
    updateSimBanner();
  } else {
    simBanner.style.display = 'none';
    updateBackButton();
  }

  selectedKeyIdx = null;
  renderLayerTabs();
  renderSvg();
  resetInspector();
}

function switchKeyboard(kb) {
  if (currentKb === kb) return;
  currentKb = kb;
  currentLayer = 0;
  simStack = [0];
  momentaryHeldLayer = null;
  layerHistory = [];
  selectedKeyIdx = null;
  document.getElementById('btn-glove80').classList.toggle('active', kb === 'glove80');
  document.getElementById('btn-go60').classList.toggle('active', kb === 'go60');
  updateHeader();
  updateBackButton();
  if (viewerMode === 'simulate') updateSimBanner();
  renderLayerTabs();
  renderSvg();
  resetInspector();
}

function updateHeader() {
  const kb = KEYBOARDS[currentKb];
  const match = kb.title.match(/v[0-9]+/);
  document.getElementById('kb-version').textContent = match ? match[0] : 'v24';
}

function toggleRgb() {
  rgbEnabled = !rgbEnabled;
  const btn = document.getElementById('btn-rgb');
  const svg = document.getElementById('keyboard-svg');
  btn.textContent = `RGB Underglow: ${rgbEnabled ? 'ON' : 'OFF'}`;
  btn.classList.toggle('active', rgbEnabled);
  svg.classList.toggle('rgb-mode', rgbEnabled);
}

function resolveCompositeKey(idx) {
  const kb = KEYBOARDS[currentKb];
  for (let i = simStack.length - 1; i >= 0; i--) {
    const layerIdx = simStack[i];
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
  for (let i = simStack.length - 1; i >= 0; i--) {
    const layerIdx = simStack[i];
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

function resetSimStack() {
  simStack = [0];
  momentaryHeldLayer = null;
  updateSimBanner();
  updateLayerTabStates();
  renderSvg();
  if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
}

function updateSimBanner() {
  const display = document.getElementById('sim-stack-display');
  const kb = KEYBOARDS[currentKb];
  const tags = simStack.map(idx => {
    const name = kb.layers[idx] ? kb.layers[idx].name : `L${idx}`;
    const isMom = (idx === momentaryHeldLayer);
    return `<span class="sim-stack-tag" style="${isMom ? 'background:#9e6a03; border-color:#d29922; color:#fff;' : ''}">${idx}: ${name}${isMom ? ' (held)' : ''}</span>`;
  }).join(' ');
  display.innerHTML = tags;
}

function toggleSimLayer(layerIdx) {
  if (layerIdx === 0) {
    if (simStack.length > 1) {
      resetSimStack();
    }
    return;
  }
  const pos = simStack.indexOf(layerIdx);
  if (pos !== -1) {
    simStack.splice(pos, 1);
  } else {
    simStack.push(layerIdx);
    simStack.sort((a, b) => a - b);
  }
  updateSimBanner();
  updateLayerTabStates();
  renderSvg();
  if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
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
      const isMom = (momentaryHeldLayer === idx);
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
}

function updateLayerTabStates() {
  const kb = KEYBOARDS[currentKb];
  kb.layers.forEach((layer, idx) => {
    const btn = document.getElementById(`layer-tab-${idx}`);
    if (!btn) return;
    if (viewerMode === 'simulate') {
      const isSimActive = simStack.includes(idx);
      const isMom = (momentaryHeldLayer === idx);
      btn.className = `layer-btn ${isSimActive ? 'sim-active' : ''} ${isMom ? 'sim-momentary' : ''}`;
      btn.innerHTML = `${isSimActive ? '<span class="sim-check-icon">✓</span>' : ''}<span class="idx">${idx}</span> ${layer.name}`;
    } else {
      const isActive = (idx === currentLayer);
      btn.className = `layer-btn ${isActive ? 'active' : ''}`;
      btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
    }
  });
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
         onpointerdown="onKeyPointerDown(${idx})"
         onpointerup="onKeyPointerUp(${idx})"
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

    if (key.rawBinding && key.rawBinding.startsWith('&tog') && key.targetLayer !== null) {
      toggleSimLayer(key.targetLayer);
      selectedKeyIdx = idx;
      inspectKey(idx);
      return;
    }

    if (key.rawBinding && key.rawBinding.startsWith('&to') && key.targetLayer !== null) {
      simStack = [key.targetLayer];
      updateSimBanner();
      updateLayerTabStates();
      renderSvg();
      selectedKeyIdx = idx;
      inspectKey(idx);
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

function onKeyPointerDown(idx) {
  if (viewerMode !== 'simulate') return;
  const { key } = resolveCompositeKey(idx);

  // Momentary activation on press-and-hold
  if (key && key.targetLayer !== null && key.targetLayer !== undefined && !key.rawBinding.startsWith('&tog') && !key.rawBinding.startsWith('&to')) {
    if (!simStack.includes(key.targetLayer)) {
      simStack.push(key.targetLayer);
      simStack.sort((a, b) => a - b);
      momentaryHeldLayer = key.targetLayer;
      updateSimBanner();
      updateLayerTabStates();
      renderSvg();
    }
  }
}

function onKeyPointerUp(idx) {
  if (viewerMode !== 'simulate') return;
  if (momentaryHeldLayer !== null) {
    const pos = simStack.indexOf(momentaryHeldLayer);
    if (pos !== -1) {
      simStack.splice(pos, 1);
    }
    momentaryHeldLayer = null;
    updateSimBanner();
    updateLayerTabStates();
    renderSvg();
  }
}

function onKeyHover(idx) {
  // In Inspect Mode: NO JUMPING / NO PREVIEW! Calmly update inspector
  if (viewerMode === 'inspect') {
    inspectKey(idx);
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
    document.getElementById('insp-title').textContent = 'Simulation Mode: Press & hold layer keys on the board to stack, or click to toggle';
    document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Toggle Layer • [M] Switch to Inspect • [Esc] Reset Stack • [G/O] Glove80/Go60';
  } else {
    document.getElementById('insp-title').textContent = 'Inspect Mode: Click any key to inspect details or navigate layers';
    document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Layer • [M] Switch to Simulate • [Esc] Back • [G/O] Glove80/Go60 • [R] RGB';
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
