const KEYBOARDS = JSON.parse(document.getElementById('embedded-data').textContent);
    let currentKb = 'glove80';
    let currentLayer = 0;
    let previewLayer = null;
    let previewTriggerKeyIdx = null;
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
            setLayer(idx);
          }
        } else if (e.key === 'g' || e.key === 'G') {
          switchKeyboard('glove80');
        } else if (e.key === 'o' || e.key === 'O') {
          switchKeyboard('go60');
        } else if (e.key === 'r' || e.key === 'R') {
          toggleRgb();
        } else if (e.key === '/') {
          e.preventDefault();
          document.getElementById('search-input').focus();
        } else if (e.key === 'Escape') {
          if (previewLayer !== null || previewTriggerKeyIdx !== null) {
            stopPreview();
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

      // Bulletproof move-away detection for layer preview:
      // Instantly disables preview the moment mouse moves off the trigger key
      document.addEventListener('pointermove', (e) => {
        if (previewTriggerKeyIdx === null) return;
        const targetKey = e.target.closest('[data-idx]');
        const hoveredIdx = targetKey ? parseInt(targetKey.getAttribute('data-idx'), 10) : null;
        if (hoveredIdx !== previewTriggerKeyIdx) {
          stopPreview();
        }
      });

      document.addEventListener('mouseleave', () => {
        if (previewTriggerKeyIdx !== null) {
          stopPreview();
        }
      });
    }

    function switchKeyboard(kb) {
      if (currentKb === kb) return;
      currentKb = kb;
      currentLayer = 0;
      previewLayer = null;
      layerHistory = [];
      selectedKeyIdx = null;
      document.getElementById('btn-glove80').classList.toggle('active', kb === 'glove80');
      document.getElementById('btn-go60').classList.toggle('active', kb === 'go60');
      updateHeader();
      updateBackButton();
      updatePreviewBanner();
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

    function renderLayerTabs() {
      const kb = KEYBOARDS[currentKb];
      const bar = document.getElementById('layer-tabs');
      bar.innerHTML = '';

      kb.layers.forEach((layer, idx) => {
        const btn = document.createElement('button');
        btn.id = `layer-tab-${idx}`;
        const isActive = (idx === currentLayer && previewLayer === null);
        const isPreview = (idx === previewLayer);
        btn.className = `layer-btn ${isActive ? 'active' : ''} ${isPreview ? 'preview-active' : ''}`;
        btn.innerHTML = `<span class="idx">${idx}</span> ${layer.name}`;
        btn.onclick = () => setLayer(idx);
        btn.onmouseenter = () => {
          if (idx !== currentLayer) {
            previewLayer = idx;
            updateLayerTabStates();
            renderSvg();
            updatePreviewBanner();
          }
        };
        btn.onmouseleave = () => {
          if (previewLayer === idx && previewTriggerKeyIdx === null) {
            previewLayer = null;
            updateLayerTabStates();
            renderSvg();
            updatePreviewBanner();
          }
        };
        bar.appendChild(btn);
      });
    }

    function updateLayerTabStates() {
      const kb = KEYBOARDS[currentKb];
      kb.layers.forEach((layer, idx) => {
        const btn = document.getElementById(`layer-tab-${idx}`);
        if (btn) {
          const isActive = (idx === currentLayer && previewLayer === null);
          const isPreview = (idx === previewLayer);
          btn.className = `layer-btn ${isActive ? 'active' : ''} ${isPreview ? 'preview-active' : ''}`;
        }
      });
    }

    function setLayer(idx, fromKeyLink = false) {
      if (fromKeyLink && idx !== currentLayer) {
        layerHistory.push(currentLayer);
      }
      currentLayer = idx;
      previewLayer = null;
      previewTriggerKeyIdx = null;
      updateBackButton();
      updatePreviewBanner();
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
        previewLayer = null;
        previewTriggerKeyIdx = null;
        updateBackButton();
        updatePreviewBanner();
        updateLayerTabStates();
        renderSvg();
        if (selectedKeyIdx !== null) inspectKey(selectedKeyIdx);
      } else {
        setLayer(0);
      }
    }

    function updateBackButton() {
      const btn = document.getElementById('btn-back-layer');
      if (layerHistory.length > 0) {
        const kb = KEYBOARDS[currentKb];
        const prevIdx = layerHistory[layerHistory.length - 1];
        const prevName = kb.layers[prevIdx] ? kb.layers[prevIdx].name : 'Base';
        btn.innerHTML = `↩ Back to ${prevName} (Esc)`;
        btn.style.display = 'inline-flex';
      } else {
        btn.style.display = 'none';
      }
    }

    function updatePreviewBanner() {
      const banner = document.getElementById('preview-banner');
      const nameEl = document.getElementById('preview-layer-name');
      if (previewLayer !== null) {
        const kb = KEYBOARDS[currentKb];
        const layerName = kb.layers[previewLayer] ? kb.layers[previewLayer].name : `L${previewLayer}`;
        nameEl.textContent = `${previewLayer}: ${layerName}`;
        banner.style.display = 'inline-flex';
      } else {
        banner.style.display = 'none';
      }
    }

    function renderSvg() {
      const kb = KEYBOARDS[currentKb];
      const coords = kb.coords;
      const displayLayer = (previewLayer !== null) ? previewLayer : currentLayer;
      const layer = kb.layers[displayLayer];
      const baseLayer = kb.layers[0];
      const svg = document.getElementById('keyboard-svg');

      if (currentKb === 'glove80') {
        svg.setAttribute('viewBox', '-15 -10 1000 460');
      } else {
        svg.setAttribute('viewBox', '-15 -10 970 365');
      }

      let html = '';

      coords.forEach((c, idx) => {
        const rawKey = layer.keys[idx] || { line1: '', line2: '', secondary: '', badge: '', rgbHex: '#000000', rawBinding: '' };
        const x = c.x * UNIT;
        const y = c.y * UNIT;
        const r = c.r || 0;
        const cx = x + KEY_SIZE / 2;
        const cy = y + KEY_SIZE / 2;

        let pivotX = (c.rx !== undefined) ? c.rx * UNIT : x;
        let pivotY = (c.ry !== undefined) ? c.ry * UNIT : y;

        // Pass-through (&trans) key resolution to Base layer
        const isTrans = (rawKey.line1 === '▽' || rawKey.rawBinding === '&trans');
        let key = rawKey;
        let isPassThrough = false;

        if (isTrans && displayLayer !== 0 && baseLayer && baseLayer.keys[idx]) {
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

    function startPreview(idx, targetLayer) {
      if (previewTriggerKeyIdx === idx && previewLayer === targetLayer) return;
      previewTriggerKeyIdx = idx;
      previewLayer = targetLayer;
      updateLayerTabStates();
      renderSvg();
      updatePreviewBanner();
    }

    function stopPreview() {
      if (previewTriggerKeyIdx === null && previewLayer === null) return;
      previewTriggerKeyIdx = null;
      previewLayer = null;
      updateLayerTabStates();
      renderSvg();
      updatePreviewBanner();
    }

    function onKeyClick(idx) {
      const kb = KEYBOARDS[currentKb];
      const origKey = kb.layers[currentLayer].keys[idx];

      // If clicked key links to another layer, switch permanently
      if (origKey && origKey.targetLayer !== null && origKey.targetLayer !== undefined && origKey.targetLayer !== currentLayer) {
        stopPreview();
        setLayer(origKey.targetLayer, true);
        return;
      }

      stopPreview();
      selectedKeyIdx = idx;
      renderSvg();
      inspectKey(idx);
    }

    function onKeyHover(idx) {
      if (previewTriggerKeyIdx !== null) return;
      const kb = KEYBOARDS[currentKb];
      const key = kb.layers[currentLayer].keys[idx];
      if (key && key.targetLayer !== null && key.targetLayer !== undefined && key.targetLayer !== currentLayer) {
        startPreview(idx, key.targetLayer);
      }
    }

    function inspectKey(idx) {
      const kb = KEYBOARDS[currentKb];
      const coord = kb.coords[idx];
      const displayLayer = (previewLayer !== null) ? previewLayer : currentLayer;
      const layer = kb.layers[displayLayer];
      const key = layer.keys[idx];

      const fullLabel = key.line2 ? `${key.line1} ${key.line2}` : (key.line1 || '—');
      document.getElementById('insp-label').textContent = fullLabel;

      const titleEl = document.getElementById('insp-title');
      const detailEl = document.getElementById('insp-detail');

      let rgbDesc = key.rgbToken !== '___' ? `RGB: <span style="color:${key.rgbHex}; font-weight:700;">${key.rgbToken}</span>` : 'RGB: Unlit';

      let layerJumpHtml = '';
      if (key.targetLayer !== null && key.targetLayer !== undefined) {
        const targetName = kb.layers[key.targetLayer] ? kb.layers[key.targetLayer].name : `Layer ${key.targetLayer}`;
        layerJumpHtml = `<button class="jump-layer-btn" onclick="setLayer(${key.targetLayer}, true)">Go to ${targetName} →</button>`;
      }

      titleEl.innerHTML = `<strong>${coord.label}</strong> (Key #${idx}) • Layer ${displayLayer}: <strong>${layer.name}</strong> • ${rgbDesc} ${layerJumpHtml}`;
      detailEl.innerHTML = `ZMK: <code style="color:var(--accent); background:#090d12; padding:2px 6px; border-radius:4px;">${escapeHtml(key.rawBinding)}</code> • ${escapeHtml(key.tooltip)}`;
    }

    function resetInspector() {
      document.getElementById('insp-label').textContent = '—';
      document.getElementById('insp-title').textContent = 'Hover or click any key to inspect details and preview layers';
      document.getElementById('insp-detail').textContent = 'Shortcuts: [0-9] Layer • [G] Glove80 • [O] Go60 • [R] Toggle RGB • Hover layer keys to preview';
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
