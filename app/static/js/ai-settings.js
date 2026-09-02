/**
 * TALAS AI — AI Settings Page
 * Manajemen provider, model, task config secara dinamis.
 * Tidak ada emoji/stiker. Clean, professional.
 */
'use strict';

const AISettings = (function () {

    let _token = null;
    let _presets = [];
    let _providers = [];
    let _taskConfigs = [];

    function init(token) {
        _token = token;
        loadAll();
    }

    async function api(method, path, body) {
        const opts = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${_token}`,
            },
        };
        if (body) opts.body = JSON.stringify(body);
        const r = await fetch('/api' + path, opts);
        if (!r.ok) {
            const err = await r.json().catch(() => ({ detail: r.statusText }));
            throw new Error(err.detail || r.statusText);
        }
        if (r.status === 204) return null;
        return r.json();
    }

    async function loadAll() {
        await Promise.all([
            loadProviders(),
            loadPresets(),
            loadTaskConfigs(),
            loadStatus(),
        ]);
    }

    // ------------------------------------------------------------------ //
    // PROVIDERS
    // ------------------------------------------------------------------ //

    async function loadProviders() {
        try {
            _providers = await api('GET', '/ai/providers');
            renderProviders();
        } catch (e) {
            showError('provider-list', e.message);
        }
    }

    function renderProviders() {
        const el = document.getElementById('provider-list');
        if (!el) return;

        if (_providers.length === 0) {
            el.innerHTML = '<p class="ai-empty">Belum ada provider. Tambah provider dari daftar preset di bawah.</p>';
            return;
        }

        el.innerHTML = _providers.map(p => `
            <div class="ai-provider-card ${p.is_enabled ? '' : 'disabled'}" id="pcard-${p.name}">
                <div class="ai-provider-header">
                    <div>
                        <div class="ai-provider-name">${escHtml(p.display_name)}</div>
                        <div class="ai-provider-meta">
                            <span class="ai-badge ${p.is_cloud ? 'cloud' : 'local'}">${p.is_cloud ? 'Cloud' : 'Lokal'}</span>
                            <span class="ai-badge ${p.is_enabled ? 'enabled' : 'disabled'}">${p.is_enabled ? 'Aktif' : 'Nonaktif'}</span>
                            ${p.last_health_check ? `<span class="ai-badge status-${p.last_health_check}">${p.last_health_check}</span>` : ''}
                        </div>
                        ${p.description ? `<div class="ai-provider-desc">${escHtml(p.description)}</div>` : ''}
                    </div>
                    <div class="ai-provider-actions">
                        <button class="btn-ai btn-test" onclick="AISettings.testProvider('${p.name}')">Test</button>
                        <button class="btn-ai btn-edit" onclick="AISettings.showEditProvider('${p.name}')">Edit</button>
                        <button class="btn-ai btn-delete" onclick="AISettings.deleteProvider('${p.name}')">Hapus</button>
                    </div>
                </div>
                <div class="ai-provider-details">
                    ${p.base_url ? `<span class="ai-detail-item">URL: <code>${escHtml(p.base_url)}</code></span>` : ''}
                    ${p.requires_api_key ? `<span class="ai-detail-item">API Key: ${p.has_api_key ? `tersimpan (${escHtml(p.api_key_hint || '...')})` : '<strong>belum dikonfigurasi</strong>'}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    async function testProvider(name) {
        const card = document.getElementById(`pcard-${name}`);
        if (card) card.style.opacity = '0.6';
        try {
            const r = await api('POST', `/ai/providers/${name}/test`);
            showToast(`${name}: ${r.status} — ${r.message}`,
                r.status === 'connected' ? 'success' : 'warning');
            await loadProviders();
        } catch (e) {
            showToast(`${name}: ${e.message}`, 'error');
        } finally {
            if (card) card.style.opacity = '1';
        }
    }

    async function deleteProvider(name) {
        if (!confirm(`Hapus provider "${name}"? Task config yang menggunakan provider ini akan terpengaruh.`)) return;
        try {
            await api('DELETE', `/ai/providers/${name}`);
            showToast(`Provider ${name} berhasil dihapus.`, 'success');
            await loadAll();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    function showEditProvider(name) {
        const p = _providers.find(x => x.name === name);
        if (!p) return;
        openProviderModal({
            mode: 'edit',
            name: p.name,
            display_name: p.display_name,
            base_url: p.base_url || '',
            is_enabled: p.is_enabled,
            is_cloud: p.is_cloud,
            requires_api_key: p.requires_api_key,
            description: p.description || '',
            api_key_hint: p.api_key_hint || '',
            has_api_key: p.has_api_key,
            provider_type: p.provider_type,
        });
    }

    // ------------------------------------------------------------------ //
    // PRESETS
    // ------------------------------------------------------------------ //

    async function loadPresets() {
        try {
            _presets = await api('GET', '/ai/presets');
            renderPresets();
        } catch (e) {
            showError('preset-list', e.message);
        }
    }

    function renderPresets() {
        const el = document.getElementById('preset-list');
        if (!el) return;

        const existingNames = new Set(_providers.map(p => p.name));

        el.innerHTML = _presets.map(preset => {
            const added = existingNames.has(preset.key);
            return `
                <div class="ai-preset-card ${added ? 'added' : ''}">
                    <div class="ai-preset-header">
                        <div class="ai-preset-name">${escHtml(preset.display_name)}</div>
                        <span class="ai-badge ${preset.is_cloud ? 'cloud' : 'local'}">${preset.is_cloud ? 'Cloud' : 'Lokal'}</span>
                    </div>
                    <div class="ai-preset-desc">${escHtml(preset.description)}</div>
                    ${preset.base_url ? `<div class="ai-preset-url"><code>${escHtml(preset.base_url)}</code></div>` : ''}
                    <div class="ai-preset-footer">
                        ${added
                            ? '<span class="ai-badge enabled">Sudah ditambahkan</span>'
                            : `<button class="btn-ai btn-add" onclick="AISettings.addFromPreset('${preset.key}', ${preset.requires_api_key})">
                                Tambah${preset.requires_api_key ? ' (perlu API Key)' : ''}
                               </button>`
                        }
                    </div>
                </div>
            `;
        }).join('');
    }

    async function addFromPreset(key, requiresApiKey) {
        let apiKey = null;
        if (requiresApiKey) {
            apiKey = prompt(`Masukkan API Key untuk ${key}:\n(Akan disimpan terenkripsi, tidak dapat dibaca kembali)`);
            if (apiKey === null) return; // cancel
            if (!apiKey.trim()) {
                showToast('API Key tidak boleh kosong untuk provider ini.', 'error');
                return;
            }
        }
        try {
            const url = `/ai/providers/from-preset/${key}${apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ''}`;
            await api('POST', url);
            showToast(`Provider ${key} berhasil ditambahkan.`, 'success');
            await loadAll();
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    // ------------------------------------------------------------------ //
    // MODAL TAMBAH/EDIT PROVIDER
    // ------------------------------------------------------------------ //

    function openProviderModal(data = {}) {
        const modal = document.getElementById('provider-modal');
        if (!modal) return;

        const isEdit = data.mode === 'edit';
        document.getElementById('modal-title').textContent = isEdit ? 'Edit Provider' : 'Tambah Provider Kustom';
        document.getElementById('modal-name').value = data.name || '';
        document.getElementById('modal-name').disabled = isEdit;
        document.getElementById('modal-display-name').value = data.display_name || '';
        document.getElementById('modal-base-url').value = data.base_url || '';
        document.getElementById('modal-is-enabled').checked = data.is_enabled !== false;
        document.getElementById('modal-is-cloud').checked = data.is_cloud || false;
        document.getElementById('modal-requires-key').checked = data.requires_api_key || false;
        document.getElementById('modal-description').value = data.description || '';
        document.getElementById('modal-mode').value = isEdit ? 'edit' : 'create';

        const keySection = document.getElementById('modal-key-section');
        const keyHint = document.getElementById('modal-key-hint');
        if (data.requires_api_key || data.has_api_key) {
            keySection.style.display = 'block';
            if (data.has_api_key && data.api_key_hint) {
                keyHint.textContent = `API key tersimpan (${data.api_key_hint}). Kosongkan untuk tidak mengubah.`;
            } else {
                keyHint.textContent = '';
            }
        } else {
            keySection.style.display = 'none';
        }

        document.getElementById('modal-requires-key').addEventListener('change', function () {
            keySection.style.display = this.checked ? 'block' : 'none';
        });

        modal.style.display = 'flex';
    }

    function closeProviderModal() {
        const modal = document.getElementById('provider-modal');
        if (modal) modal.style.display = 'none';
        document.getElementById('provider-form').reset();
    }

    async function submitProviderForm(e) {
        e.preventDefault();
        const mode = document.getElementById('modal-mode').value;
        const name = document.getElementById('modal-name').value.trim();
        const apiKey = document.getElementById('modal-api-key').value.trim();

        const payload = {
            display_name: document.getElementById('modal-display-name').value.trim(),
            base_url: document.getElementById('modal-base-url').value.trim() || null,
            is_enabled: document.getElementById('modal-is-enabled').checked,
            is_cloud: document.getElementById('modal-is-cloud').checked,
            requires_api_key: document.getElementById('modal-requires-key').checked,
            description: document.getElementById('modal-description').value.trim() || null,
            api_key: apiKey || (mode === 'edit' ? null : undefined),
        };

        try {
            if (mode === 'create') {
                payload.name = name;
                payload.provider_type = 'custom';
                await api('POST', '/ai/providers', payload);
                showToast('Provider berhasil ditambahkan.', 'success');
            } else {
                await api('PUT', `/ai/providers/${name}`, payload);
                showToast('Provider berhasil diupdate.', 'success');
            }
            closeProviderModal();
            await loadAll();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }

    // ------------------------------------------------------------------ //
    // TASK CONFIG
    // ------------------------------------------------------------------ //

    async function loadTaskConfigs() {
        try {
            const data = await api('GET', '/ai/task-configs');
            _taskConfigs = data.tasks || [];
            renderTaskConfigs(data.available_providers || []);
        } catch (e) {
            showError('task-config-list', e.message);
        }
    }

    function renderTaskConfigs(availableProviders) {
        const el = document.getElementById('task-config-list');
        if (!el) return;

        if (availableProviders.length === 0) {
            el.innerHTML = '<p class="ai-empty">Tidak ada provider aktif. Aktifkan provider terlebih dahulu.</p>';
            return;
        }

        el.innerHTML = _taskConfigs.map(task => `
            <div class="ai-task-row" id="task-row-${task.task_name}">
                <div class="ai-task-label">${escHtml(task.task_label)}</div>
                <div class="ai-task-config">
                    <select class="ai-select" id="task-provider-${task.task_name}"
                            onchange="AISettings.onTaskProviderChange('${task.task_name}')">
                        <option value="">-- Pilih Provider --</option>
                        ${availableProviders.map(p =>
                            `<option value="${escHtml(p)}" ${task.provider_name === p ? 'selected' : ''}>${escHtml(p)}</option>`
                        ).join('')}
                    </select>
                    <input type="text" class="ai-input" id="task-model-${task.task_name}"
                           placeholder="Model ID (contoh: llama3.2:3b)"
                           value="${escHtml(task.model_id || '')}"
                           list="models-${task.task_name}">
                    <datalist id="models-${task.task_name}"></datalist>
                    <input type="number" class="ai-input ai-input-sm" id="task-temp-${task.task_name}"
                           placeholder="Temp" value="${task.temperature || 0.1}"
                           min="0" max="2" step="0.05">
                    <button class="btn-ai btn-save" onclick="AISettings.saveTaskConfig('${task.task_name}')">Simpan</button>
                </div>
            </div>
        `).join('');
    }

    async function onTaskProviderChange(taskName) {
        const providerName = document.getElementById(`task-provider-${taskName}`).value;
        if (!providerName) return;
        try {
            const models = await api('GET', `/ai/providers/${providerName}/models`);
            const datalist = document.getElementById(`models-${taskName}`);
            if (datalist) {
                datalist.innerHTML = models.map(m =>
                    `<option value="${escHtml(m.model_id)}">${escHtml(m.display_name)}</option>`
                ).join('');
            }
        } catch (e) {
            // Silent — model list opsional
        }
    }

    async function saveTaskConfig(taskName) {
        const providerName = document.getElementById(`task-provider-${taskName}`).value;
        const modelId = document.getElementById(`task-model-${taskName}`).value.trim();
        const temperature = parseFloat(document.getElementById(`task-temp-${taskName}`).value) || 0.1;

        if (!providerName || !modelId) {
            showToast('Provider dan Model harus diisi.', 'error');
            return;
        }

        try {
            await api('PUT', '/ai/task-configs', {
                task_name: taskName,
                provider_name: providerName,
                model_id: modelId,
                temperature,
            });
            showToast(`Task "${taskName}" berhasil disimpan.`, 'success');
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    // ------------------------------------------------------------------ //
    // LIVE STATUS
    // ------------------------------------------------------------------ //

    async function loadStatus() {
        try {
            const statuses = await api('GET', '/ai/status');
            renderLiveStatus(statuses);
        } catch (e) {
            // Silent fail
        }
    }

    function renderLiveStatus(statuses) {
        const el = document.getElementById('ai-live-status');
        if (!el) return;

        if (!statuses || statuses.length === 0) {
            el.innerHTML = '<p class="ai-empty">Tidak ada provider aktif.</p>';
            return;
        }

        el.innerHTML = statuses.map(s => `
            <div class="ai-status-row">
                <span class="ai-status-dot ${s.status === 'connected' ? 'green' : s.status === 'error' ? 'red' : 'yellow'}"></span>
                <span class="ai-status-name">${escHtml(s.name)}</span>
                <span class="ai-status-msg">${escHtml(s.message)}</span>
                ${s.models_available > 0 ? `<span class="ai-badge enabled">${s.models_available} model</span>` : ''}
                ${s.is_cloud ? '<span class="ai-badge cloud">Cloud</span>' : '<span class="ai-badge local">Lokal</span>'}
            </div>
        `).join('');
    }

    // ------------------------------------------------------------------ //
    // PRIVACY MODE
    // ------------------------------------------------------------------ //

    async function updatePrivacyMode(mode) {
        try {
            const r = await api('PUT', '/ai/settings/privacy', { mode });
            showToast(`Mode privasi diubah ke: ${mode}`, 'success');
            document.querySelectorAll('.privacy-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === mode);
            });
        } catch (e) {
            showToast(e.message, 'error');
        }
    }

    // ------------------------------------------------------------------ //
    // Utilities
    // ------------------------------------------------------------------ //

    function escHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function showToast(msg, type = 'success') {
        const el = document.getElementById('ai-toast');
        if (!el) return;
        el.textContent = msg;
        el.className = `ai-toast ai-toast-${type} show`;
        setTimeout(() => el.classList.remove('show'), 4000);
    }

    function showError(containerId, msg) {
        const el = document.getElementById(containerId);
        if (el) el.innerHTML = `<p class="ai-error">Error: ${escHtml(msg)}</p>`;
    }

    // Public API
    return {
        init,
        loadAll,
        loadProviders,
        testProvider,
        deleteProvider,
        showEditProvider,
        addFromPreset,
        openProviderModal,
        closeProviderModal,
        submitProviderForm,
        onTaskProviderChange,
        saveTaskConfig,
        updatePrivacyMode,
    };

})();
