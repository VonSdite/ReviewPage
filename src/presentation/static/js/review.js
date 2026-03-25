(function() {
    const state = {
        meta: null,
        settings: null,
        records: [],
        openDetailId: null,
        openDetailRecord: null,
        refreshTimer: null,
        autoRefreshEnabled: false,
        page: 1,
        pageSize: 50,
        totalPages: 1,
        totalRecords: 0,
        jumpDebounceTimer: null,
        activePageTab: 'review',
        activeSettingsTab: 'agents',
        activeAgentSettingsId: '',
        activeHubSettingsId: ''
    };

    const elements = {};

    function cacheElements() {
        elements.pageTopbarTitle = document.getElementById('pageTopbarTitle');
        elements.pageTopbarSummary = document.getElementById('pageTopbarSummary');
        elements.reviewForm = document.getElementById('reviewForm');
        elements.mrUrlInput = document.getElementById('mrUrlInput');
        elements.hubSelect = document.getElementById('hubSelect');
        elements.agentSelect = document.getElementById('agentSelect');
        elements.modelSelect = document.getElementById('modelSelect');
        elements.hubSetDefaultQuickButton = document.getElementById('hubSetDefaultQuickButton');
        elements.agentSetDefaultQuickButton = document.getElementById('agentSetDefaultQuickButton');
        elements.modelSetDefaultQuickButton = document.getElementById('modelSetDefaultQuickButton');
        elements.modelRefreshQuickButton = document.getElementById('modelRefreshQuickButton');
        elements.modelHint = document.getElementById('modelHint');
        elements.submitButton = document.getElementById('submitButton');

        elements.pageTabButtons = Array.from(document.querySelectorAll('[data-page-tab-target]'));
        elements.pagePanels = Array.from(document.querySelectorAll('[data-page-panel]'));
        elements.settingsTabButtons = Array.from(document.querySelectorAll('[data-settings-tab-target]'));
        elements.settingsPanels = Array.from(document.querySelectorAll('[data-settings-panel]'));

        elements.agentSettingsList = document.getElementById('agentSettingsList');
        elements.agentSettingsForm = document.getElementById('agentSettingsForm');
        elements.agentSettingsTitle = document.getElementById('agentSettingsTitle');
        elements.agentSettingsId = document.getElementById('agentSettingsId');
        elements.agentDefaultPill = document.getElementById('agentDefaultPill');
        elements.agentListModelsCommandInput = document.getElementById('agentListModelsCommandInput');
        elements.agentReviewCommandInput = document.getElementById('agentReviewCommandInput');
        elements.agentCommandShellExecutableInput = document.getElementById('agentCommandShellExecutableInput');
        elements.agentCommandShellArgsInput = document.getElementById('agentCommandShellArgsInput');
        elements.agentDefaultModelSelect = document.getElementById('agentDefaultModelSelect');
        elements.agentModelsTextarea = document.getElementById('agentModelsTextarea');
        elements.agentExtraEnvTextarea = document.getElementById('agentExtraEnvTextarea');
        elements.agentSettingsHint = document.getElementById('agentSettingsHint');
        elements.agentSetDefaultButton = document.getElementById('agentSetDefaultButton');
        elements.agentRefreshModelsButton = document.getElementById('agentRefreshModelsButton');
        elements.agentSaveButton = document.getElementById('agentSaveButton');

        elements.hubSettingsList = document.getElementById('hubSettingsList');
        elements.hubSettingsForm = document.getElementById('hubSettingsForm');
        elements.hubSettingsTitle = document.getElementById('hubSettingsTitle');
        elements.hubSettingsId = document.getElementById('hubSettingsId');
        elements.hubDefaultPill = document.getElementById('hubDefaultPill');
        elements.hubTypePill = document.getElementById('hubTypePill');
        elements.hubTypeSelect = document.getElementById('hubTypeSelect');
        elements.hubWebBaseUrlInput = document.getElementById('hubWebBaseUrlInput');
        elements.hubApiBaseUrlInput = document.getElementById('hubApiBaseUrlInput');
        elements.hubPrivateTokenInput = document.getElementById('hubPrivateTokenInput');
        elements.hubClonePreferenceSelect = document.getElementById('hubClonePreferenceSelect');
        elements.hubTimeoutInput = document.getElementById('hubTimeoutInput');
        elements.hubVerifySslInput = document.getElementById('hubVerifySslInput');
        elements.hubSettingsHint = document.getElementById('hubSettingsHint');
        elements.hubSetDefaultButton = document.getElementById('hubSetDefaultButton');
        elements.hubSaveButton = document.getElementById('hubSaveButton');

        elements.queueRefreshButton = document.getElementById('queueRefreshButton');
        elements.autoRefreshToggleButton = document.getElementById('autoRefreshToggleButton');
        elements.tableFooter = document.getElementById('tableFooter');
        elements.prevBtn = document.getElementById('prevBtn');
        elements.nextBtn = document.getElementById('nextBtn');
        elements.pageInfo = document.getElementById('pageInfo');
        elements.pageJumpInput = document.getElementById('pageJumpInput');
        elements.pageSizeSelect = document.getElementById('pageSizeSelect');
        elements.totalCount = document.getElementById('totalCount');
        elements.recordsTableBody = document.getElementById('recordsTableBody');
        elements.toastStack = document.getElementById('toastStack');

        elements.detailModal = document.getElementById('detailModal');
        elements.detailPrefillButton = document.getElementById('detailPrefillButton');
        elements.detailStatusPill = document.getElementById('detailStatusPill');
        elements.detailContent = document.getElementById('detailContent');
        elements.detailMrUrl = document.getElementById('detailMrUrl');
        elements.detailHub = document.getElementById('detailHub');
        elements.detailAgent = document.getElementById('detailAgent');
        elements.detailModel = document.getElementById('detailModel');
        elements.detailSourceBranch = document.getElementById('detailSourceBranch');
        elements.detailTargetBranch = document.getElementById('detailTargetBranch');
        elements.detailCreatedAt = document.getElementById('detailCreatedAt');
        elements.detailStartedAt = document.getElementById('detailStartedAt');
        elements.detailFinishedAt = document.getElementById('detailFinishedAt');
        elements.detailCommand = document.getElementById('detailCommand');
        elements.detailLogs = document.getElementById('detailLogs');
    }

    function formatDate(value) {
        if (!value) {
            return '-';
        }

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString('zh-CN', { hour12: false });
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function stripTerminalControlSequences(value) {
        return String(value == null ? '' : value)
            .replace(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)/g, '')
            .replace(/(?:\u001b[@-_][0-?]*[ -/]*[@-~])|(?:\u009b[0-?]*[ -/]*[@-~])/g, '')
            .replace(/\ufffd\[[0-?]*[ -/]*[@-~]/g, '')
            .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g, '');
    }

    function showToast(message, variant) {
        if (!elements.toastStack) {
            return;
        }

        const item = document.createElement('div');
        item.className = `toast ${variant ? `toast-${variant}` : ''}`.trim();
        item.textContent = String(message || '未知错误');
        elements.toastStack.appendChild(item);
        window.setTimeout(function() {
            item.remove();
        }, 3600);
    }

    async function requestJson(url, options) {
        const response = await fetch(url, options);
        let payload = {};

        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }

        if (!response.ok) {
            throw new Error(payload.error || `Request failed (${response.status})`);
        }

        return payload;
    }

    async function runWithBusyButton(button, busyText, action) {
        const originalText = button.textContent;
        button.disabled = true;
        button.classList.add('is-loading');
        button.textContent = busyText;

        try {
            return await action();
        } finally {
            button.disabled = false;
            button.classList.remove('is-loading');
            button.textContent = originalText;
        }
    }

    function parseLineList(value) {
        const seen = new Set();
        return String(value || '')
            .split(/\r?\n/g)
            .map(function(item) {
                return item.trim();
            })
            .filter(function(item) {
                if (!item || seen.has(item)) {
                    return false;
                }
                seen.add(item);
                return true;
            });
    }

    function joinLineList(items) {
        return (Array.isArray(items) ? items : [])
            .map(function(item) {
                return String(item || '').trim();
            })
            .filter(Boolean)
            .join('\n');
    }

    function formatJson(value) {
        return JSON.stringify(value || {}, null, 2);
    }

    function parseJsonObject(text, fieldName) {
        const source = String(text || '').trim();
        if (!source) {
            return {};
        }

        let parsed;
        try {
            parsed = JSON.parse(source);
        } catch (error) {
            throw new Error(`${fieldName} must be a valid JSON object.`);
        }

        if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
            throw new Error(`${fieldName} must be a JSON object.`);
        }

        return Object.fromEntries(
            Object.entries(parsed).map(function(entry) {
                return [String(entry[0]), String(entry[1])];
            })
        );
    }

    function appendOption(select, value, label, options) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        option.disabled = Boolean(options && options.disabled);
        option.selected = Boolean(options && options.selected);
        select.appendChild(option);
    }

    function findAgentMeta(agentId) {
        if (!state.meta) {
            return null;
        }

        return state.meta.agents.find(function(agent) {
            return agent.id === agentId;
        }) || null;
    }

    function findHubMeta(hubId) {
        if (!state.meta) {
            return null;
        }

        return state.meta.hubs.find(function(hub) {
            return hub.id === hubId;
        }) || null;
    }

    function findSettingsAgent(agentId) {
        if (!state.settings) {
            return null;
        }

        return state.settings.agents.find(function(agent) {
            return agent.id === agentId;
        }) || null;
    }

    function findSettingsHub(hubId) {
        if (!state.settings) {
            return null;
        }

        return state.settings.hubs.find(function(hub) {
            return hub.id === hubId;
        }) || null;
    }

    function collectAgentModelIds(agentData) {
        const fromMeta = Array.isArray(agentData && agentData.models)
            ? agentData.models.map(function(model) {
                return String(model.id || '').trim();
            })
            : [];
        const fromConfig = Array.isArray(agentData && agentData.config && agentData.config.models)
            ? agentData.config.models.map(function(model) {
                return String(model || '').trim();
            })
            : [];
        return parseLineList(fromMeta.concat(fromConfig).join('\n'));
    }

    function setModelHint(message) {
        const text = String(message || '').trim();
        elements.modelHint.textContent = text;
        elements.modelHint.hidden = !text;
    }

    function formatDefaultOptionLabel(label, isDefault) {
        const text = String(label || '').trim();
        if (!text) {
            return '';
        }
        return isDefault ? `${text}\u00a0\u00a0⭐` : text;
    }

    function setQuickActionButtonState(button, options) {
        if (!button) {
            return;
        }

        const settings = options || {};
        const text = String(settings.text || '').trim();
        const title = String(settings.title || text).trim();

        button.disabled = Boolean(settings.disabled);
        if (text) {
            button.textContent = text;
        }
        if (title) {
            button.setAttribute('title', title);
            button.setAttribute('aria-label', title);
        } else {
            button.removeAttribute('title');
            button.removeAttribute('aria-label');
        }
    }

    function syncReviewFormQuickActions() {
        const defaults = state.meta && state.meta.defaults ? state.meta.defaults : {};
        const selectedHubId = String(elements.hubSelect && elements.hubSelect.value || '').trim();
        const selectedAgentId = String(elements.agentSelect && elements.agentSelect.value || '').trim();
        const selectedModelId = String(elements.modelSelect && elements.modelSelect.value || '').trim();
        const selectedHub = findHubMeta(selectedHubId);
        const selectedAgent = findAgentMeta(selectedAgentId);
        const defaultHubId = String(defaults.hub_id || '').trim();
        const defaultAgentId = String(defaults.agent_id || '').trim();
        const defaultModelId = String((selectedAgent && selectedAgent.default_model_id) || '').trim();

        setQuickActionButtonState(elements.hubSetDefaultQuickButton, {
            disabled: !selectedHubId || !selectedHub || selectedHubId === defaultHubId,
            text: selectedHubId && selectedHubId === defaultHubId ? '默认平台' : '设为默认',
            title: !selectedHubId
                ? '请先选择平台'
                : selectedHubId === defaultHubId
                    ? '当前平台已是默认平台'
                    : '将当前平台设置为默认平台'
        });

        setQuickActionButtonState(elements.agentSetDefaultQuickButton, {
            disabled: !selectedAgentId || !selectedAgent || selectedAgentId === defaultAgentId,
            text: selectedAgentId && selectedAgentId === defaultAgentId ? '默认 Agent' : '设为默认',
            title: !selectedAgentId
                ? '请先选择 Agent'
                : selectedAgentId === defaultAgentId
                    ? '当前 Agent 已是默认 Agent'
                    : '将当前 Agent 设置为默认 Agent'
        });

        setQuickActionButtonState(elements.modelSetDefaultQuickButton, {
            disabled: !selectedAgentId || !selectedModelId || selectedModelId === defaultModelId,
            text: selectedModelId && selectedModelId === defaultModelId ? '默认模型' : '设为默认',
            title: !selectedAgentId
                ? '请先选择 Agent'
                : !selectedModelId
                    ? '请先选择模型'
                    : selectedModelId === defaultModelId
                        ? '当前模型已是默认模型'
                        : '将当前模型设置为默认模型'
        });

        setQuickActionButtonState(elements.modelRefreshQuickButton, {
            disabled: !selectedAgentId,
            text: '更新模型',
            title: selectedAgentId ? '刷新当前 Agent 的模型列表' : '请先选择 Agent'
        });
    }

    function formatModelOptionLabel(model, defaultModelId) {
        const label = String((model && (model.label || model.id)) || '').trim();
        if (!label) {
            return '';
        }
        return formatDefaultOptionLabel(label, Boolean(model && model.id === defaultModelId));
    }

    function isAvailableModel(agentMeta, modelId) {
        if (!agentMeta || !modelId) {
            return false;
        }

        return (agentMeta.models || []).some(function(model) {
            return model.id === modelId;
        });
    }

    function syncPageTopbar(tabId) {
        const activePanel = elements.pagePanels.find(function(panel) {
            return panel.getAttribute('data-page-panel') === tabId;
        });

        if (!activePanel) {
            return;
        }

        const nextTitle = String(activePanel.getAttribute('data-page-title') || '').trim();
        const nextSummary = String(activePanel.getAttribute('data-page-summary') || '').trim();

        if (elements.pageTopbarTitle && nextTitle) {
            elements.pageTopbarTitle.textContent = nextTitle;
        }

        if (elements.pageTopbarSummary) {
            elements.pageTopbarSummary.textContent = nextSummary;
        }
    }

    function setActivePageTab(tabId) {
        state.activePageTab = tabId;

        elements.pageTabButtons.forEach(function(button) {
            const active = button.getAttribute('data-page-tab-target') === tabId;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        elements.pagePanels.forEach(function(panel) {
            panel.hidden = panel.getAttribute('data-page-panel') !== tabId;
        });

        syncPageTopbar(tabId);
    }

    function setActiveSettingsTab(tabId) {
        state.activeSettingsTab = tabId;

        elements.settingsTabButtons.forEach(function(button) {
            const active = button.getAttribute('data-settings-tab-target') === tabId;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-selected', active ? 'true' : 'false');
        });

        elements.settingsPanels.forEach(function(panel) {
            panel.hidden = panel.getAttribute('data-settings-panel') !== tabId;
        });
    }

    function syncAutoRefreshUi() {
        if (state.autoRefreshEnabled) {
            elements.autoRefreshToggleButton.textContent = '自动刷新: 开';
            elements.autoRefreshToggleButton.classList.add('is-active');
            return;
        }

        elements.autoRefreshToggleButton.textContent = '自动刷新: 关';
        elements.autoRefreshToggleButton.classList.remove('is-active');
    }

    function setAutoRefresh(enabled) {
        state.autoRefreshEnabled = Boolean(enabled);

        if (state.refreshTimer) {
            window.clearInterval(state.refreshTimer);
            state.refreshTimer = null;
        }

        if (state.autoRefreshEnabled) {
            state.refreshTimer = window.setInterval(function() {
                refreshReviews().catch(function(error) {
                    showToast(error.message || String(error), 'error');
                    setAutoRefresh(false);
                });
            }, 4000);
        }

        syncAutoRefreshUi();
    }

    function populateHubSelect(preferredHubId) {
        const hubs = state.meta && Array.isArray(state.meta.hubs) ? state.meta.hubs : [];
        const defaults = state.meta && state.meta.defaults ? state.meta.defaults : {};
        const defaultHubId = String(defaults.hub_id || '').trim();
        const fallbackHubId = hubs[0] ? hubs[0].id : '';
        const desiredHubId = [preferredHubId, defaults.hub_id, fallbackHubId].find(function(hubId) {
            return hubs.some(function(hub) {
                return hub.id === hubId;
            });
        }) || '';

        elements.hubSelect.innerHTML = '';
        hubs.forEach(function(hub) {
            appendOption(
                elements.hubSelect,
                hub.id,
                formatDefaultOptionLabel(hub.name || hub.id, hub.id === defaultHubId),
                { selected: hub.id === desiredHubId }
            );
        });

        syncReviewFormQuickActions();
    }

    function updateModelSuggestions(preferredModelId) {
        const agentMeta = findAgentMeta(elements.agentSelect.value);
        const currentModelId = String(elements.modelSelect.value || '').trim();
        const defaultModelId = String((agentMeta && agentMeta.default_model_id) || '').trim();
        const models = agentMeta ? agentMeta.models || [] : [];

        elements.modelSelect.innerHTML = '';

        if (!agentMeta) {
            appendOption(elements.modelSelect, '', '暂无可用智能体', { disabled: true, selected: true });
            setModelHint('');
            syncReviewFormQuickActions();
            return;
        }

        if (!models.length) {
            appendOption(elements.modelSelect, '', '暂无可用模型', { disabled: true, selected: true });
            setModelHint(agentMeta.model_error || '请到系统设置中刷新并保存该智能体的模型列表。');
            syncReviewFormQuickActions();
            return;
        }

        models.forEach(function(model) {
            appendOption(elements.modelSelect, model.id, formatModelOptionLabel(model, defaultModelId));
        });

        const selectedModelId = [preferredModelId, currentModelId, defaultModelId]
            .find(function(modelId) {
                return isAvailableModel(agentMeta, modelId);
            }) || models[0].id;

        elements.modelSelect.value = selectedModelId;
        setModelHint('');
        syncReviewFormQuickActions();
    }

    function populateAgentSelect(preferredAgentId, preferredModelId) {
        const agents = state.meta && Array.isArray(state.meta.agents) ? state.meta.agents : [];
        const defaults = state.meta && state.meta.defaults ? state.meta.defaults : {};
        const defaultAgentId = String(defaults.agent_id || '').trim();
        const fallbackAgentId = agents[0] ? agents[0].id : '';
        const desiredAgentId = [preferredAgentId, defaults.agent_id, fallbackAgentId].find(function(agentId) {
            return agents.some(function(agent) {
                return agent.id === agentId;
            });
        }) || '';

        elements.agentSelect.innerHTML = '';
        agents.forEach(function(agent) {
            appendOption(
                elements.agentSelect,
                agent.id,
                formatDefaultOptionLabel(agent.name || agent.id, agent.id === defaultAgentId),
                { selected: agent.id === desiredAgentId }
            );
        });

        updateModelSuggestions(preferredModelId);
    }

    function syncActiveSettingsIds() {
        const agentIds = state.settings && Array.isArray(state.settings.agents)
            ? state.settings.agents.map(function(agent) { return agent.id; })
            : [];
        const hubIds = state.settings && Array.isArray(state.settings.hubs)
            ? state.settings.hubs.map(function(hub) { return hub.id; })
            : [];

        if (!agentIds.includes(state.activeAgentSettingsId)) {
            state.activeAgentSettingsId = agentIds[0] || '';
        }
        if (!hubIds.includes(state.activeHubSettingsId)) {
            state.activeHubSettingsId = hubIds[0] || '';
        }
    }

    function renderAgentDefaultModelOptions(modelIds, selectedModelId) {
        const normalizedIds = parseLineList((modelIds || []).join('\n'));
        const normalizedSelectedId = String(selectedModelId || '').trim();

        elements.agentDefaultModelSelect.innerHTML = '';
        appendOption(elements.agentDefaultModelSelect, '', '（不设置默认模型）', {
            selected: !normalizedSelectedId
        });

        normalizedIds.forEach(function(modelId) {
            appendOption(elements.agentDefaultModelSelect, modelId, modelId, {
                selected: modelId === normalizedSelectedId
            });
        });

        if (normalizedSelectedId && !normalizedIds.includes(normalizedSelectedId)) {
            appendOption(elements.agentDefaultModelSelect, normalizedSelectedId, `[缺失] ${normalizedSelectedId}`, {
                selected: true
            });
        }
    }

    function setAgentEditorDisabled(disabled) {
        [
            elements.agentListModelsCommandInput,
            elements.agentReviewCommandInput,
            elements.agentCommandShellExecutableInput,
            elements.agentCommandShellArgsInput,
            elements.agentDefaultModelSelect,
            elements.agentModelsTextarea,
            elements.agentExtraEnvTextarea,
            elements.agentSetDefaultButton,
            elements.agentRefreshModelsButton,
            elements.agentSaveButton
        ].forEach(function(node) {
            node.disabled = disabled;
        });
    }

    function setHubEditorDisabled(disabled) {
        [
            elements.hubTypeSelect,
            elements.hubWebBaseUrlInput,
            elements.hubApiBaseUrlInput,
            elements.hubPrivateTokenInput,
            elements.hubClonePreferenceSelect,
            elements.hubTimeoutInput,
            elements.hubVerifySslInput,
            elements.hubSetDefaultButton,
            elements.hubSaveButton
        ].forEach(function(node) {
            node.disabled = disabled;
        });
    }

    function renderAgentSettingsList() {
        const agents = state.settings && Array.isArray(state.settings.agents) ? state.settings.agents : [];
        if (!agents.length) {
            elements.agentSettingsList.innerHTML = '<div class="settings-empty">暂无已配置智能体。</div>';
            return;
        }

        elements.agentSettingsList.innerHTML = agents.map(function(agent) {
            const modelCount = Array.isArray(agent.models) ? agent.models.length : 0;
            return `
                <button
                    type="button"
                    class="settings-entity-button ${agent.id === state.activeAgentSettingsId ? 'is-active' : ''}"
                    data-agent-settings-id="${escapeHtml(agent.id)}"
                >
                    <span class="settings-entity-title">${escapeHtml(agent.name || agent.id)}</span>
                    <span class="settings-entity-subtitle">default model: ${escapeHtml((agent.config && agent.config.default_model) || '(none)')}</span>
                    <span class="settings-entity-meta">
                        ${agent.is_default ? '<span class="status-pill status-queued">默认</span>' : ''}
                        <span class="status-pill">${escapeHtml(String(modelCount))} 个模型</span>
                    </span>
                </button>
            `;
        }).join('');
    }

    function renderAgentSettingsEditor() {
        const agent = findSettingsAgent(state.activeAgentSettingsId);
        if (!agent) {
            elements.agentSettingsTitle.textContent = '-';
            elements.agentSettingsId.value = '';
            elements.agentDefaultPill.hidden = true;
            elements.agentListModelsCommandInput.value = '';
            elements.agentReviewCommandInput.value = '';
            elements.agentCommandShellExecutableInput.value = '';
            elements.agentCommandShellArgsInput.value = '';
            elements.agentModelsTextarea.value = '';
            elements.agentExtraEnvTextarea.value = '{}';
            renderAgentDefaultModelOptions([], '');
            elements.agentSettingsHint.textContent = '未选择智能体。';
            setAgentEditorDisabled(true);
            return;
        }

        const config = agent.config || {};
        const commandShell = config.command_shell;
        const modelIds = collectAgentModelIds(agent);
        const selectedDefaultModel = String(config.default_model || agent.default_model_id || '').trim();

        elements.agentSettingsTitle.textContent = agent.name || agent.id;
        elements.agentSettingsId.value = agent.id;
        elements.agentDefaultPill.hidden = !agent.is_default;
        elements.agentListModelsCommandInput.value = config.list_models_command || '';
        elements.agentReviewCommandInput.value = config.review_command || '';
        elements.agentCommandShellExecutableInput.value = typeof commandShell === 'string'
            ? commandShell
            : String((commandShell && commandShell.executable) || '');
        elements.agentCommandShellArgsInput.value = typeof commandShell === 'string'
            ? ''
            : joinLineList((commandShell && commandShell.args) || []);
        elements.agentModelsTextarea.value = joinLineList(modelIds);
        elements.agentExtraEnvTextarea.value = formatJson(config.extra_env || {});
        renderAgentDefaultModelOptions(modelIds, selectedDefaultModel);
        elements.agentSettingsHint.textContent = agent.model_error
            ? `Model status: ${agent.model_error}`
            : '保存前会校验命令字段；拉取新模型会先保存当前智能体配置，再刷新模型列表。';
        setAgentEditorDisabled(false);
        elements.agentSetDefaultButton.disabled = Boolean(agent.is_default);
        elements.agentSetDefaultButton.textContent = agent.is_default ? '默认智能体' : '设为默认智能体';
    }

    function renderHubTypeOptions(selectedType) {
        const registeredTypes = state.settings && Array.isArray(state.settings.hub_types) ? state.settings.hub_types.slice() : [];
        const normalizedSelectedType = String(selectedType || '').trim();
        if (normalizedSelectedType && !registeredTypes.includes(normalizedSelectedType)) {
            registeredTypes.push(normalizedSelectedType);
        }

        elements.hubTypeSelect.innerHTML = '';
        registeredTypes.forEach(function(hubType) {
            appendOption(elements.hubTypeSelect, hubType, hubType, {
                selected: hubType === normalizedSelectedType
            });
        });
    }

    function renderHubSettingsList() {
        const hubs = state.settings && Array.isArray(state.settings.hubs) ? state.settings.hubs : [];
        if (!hubs.length) {
            elements.hubSettingsList.innerHTML = '<div class="settings-empty">暂无已配置平台。</div>';
            return;
        }

        elements.hubSettingsList.innerHTML = hubs.map(function(hub) {
            const config = hub.config || {};
            return `
                <button
                    type="button"
                    class="settings-entity-button ${hub.id === state.activeHubSettingsId ? 'is-active' : ''}"
                    data-hub-settings-id="${escapeHtml(hub.id)}"
                >
                    <span class="settings-entity-title">${escapeHtml(hub.name || hub.id)}</span>
                    <span class="settings-entity-subtitle">${escapeHtml(config.web_base_url || '(no web base url)')}</span>
                    <span class="settings-entity-meta">
                        ${hub.is_default ? '<span class="status-pill status-queued">默认</span>' : ''}
                        <span class="status-pill">类型: ${escapeHtml(hub.type || config.type || '未知')}</span>
                    </span>
                </button>
            `;
        }).join('');
    }

    function renderHubSettingsEditor() {
        const hub = findSettingsHub(state.activeHubSettingsId);
        if (!hub) {
            elements.hubSettingsTitle.textContent = '-';
            elements.hubSettingsId.value = '';
            elements.hubDefaultPill.hidden = true;
            elements.hubTypePill.textContent = '类型: -';
            renderHubTypeOptions('');
            elements.hubWebBaseUrlInput.value = '';
            elements.hubApiBaseUrlInput.value = '';
            elements.hubPrivateTokenInput.value = '';
            elements.hubClonePreferenceSelect.value = 'http';
            elements.hubTimeoutInput.value = '20';
            elements.hubVerifySslInput.checked = true;
            elements.hubSettingsHint.textContent = '未选择平台。';
            setHubEditorDisabled(true);
            return;
        }

        const config = hub.config || {};
        const hubType = hub.type || config.type || '';

        elements.hubSettingsTitle.textContent = hub.name || hub.id;
        elements.hubSettingsId.value = hub.id;
        elements.hubDefaultPill.hidden = !hub.is_default;
        elements.hubTypePill.textContent = `类型: ${hubType || '-'}`;
        renderHubTypeOptions(hubType);
        elements.hubWebBaseUrlInput.value = config.web_base_url || '';
        elements.hubApiBaseUrlInput.value = config.api_base_url || '';
        elements.hubPrivateTokenInput.value = config.private_token || '';
        elements.hubClonePreferenceSelect.value = config.clone_url_preference || 'http';
        elements.hubTimeoutInput.value = String(config.timeout_seconds == null ? 20 : config.timeout_seconds);
        elements.hubVerifySslInput.checked = config.verify_ssl !== false;
        elements.hubSettingsHint.textContent = '保存后会立即重建运行时平台实例。';
        setHubEditorDisabled(false);
        elements.hubSetDefaultButton.disabled = Boolean(hub.is_default);
        elements.hubSetDefaultButton.textContent = hub.is_default ? '默认平台' : '设为默认平台';
    }

    function renderSettings() {
        syncActiveSettingsIds();
        renderAgentSettingsList();
        renderHubSettingsList();
        renderAgentSettingsEditor();
        renderHubSettingsEditor();
    }

    async function reloadPageState(options) {
        const payload = options || {};
        const hasOwn = Object.prototype.hasOwnProperty;
        const preferredHubId = hasOwn.call(payload, 'hubId') ? payload.hubId : String(elements.hubSelect.value || '');
        const preferredAgentId = hasOwn.call(payload, 'agentId') ? payload.agentId : String(elements.agentSelect.value || '');
        const preferredModelId = hasOwn.call(payload, 'modelId') ? payload.modelId : String(elements.modelSelect.value || '');
        const preferredAgentSettingsId = hasOwn.call(payload, 'activeAgentSettingsId')
            ? payload.activeAgentSettingsId
            : state.activeAgentSettingsId;
        const preferredHubSettingsId = hasOwn.call(payload, 'activeHubSettingsId')
            ? payload.activeHubSettingsId
            : state.activeHubSettingsId;

        const results = await Promise.all([
            requestJson('/api/meta'),
            requestJson('/api/settings')
        ]);

        state.meta = results[0];
        state.settings = results[1];
        state.activeAgentSettingsId = String(preferredAgentSettingsId || '');
        state.activeHubSettingsId = String(preferredHubSettingsId || '');

        populateHubSelect(preferredHubId);
        populateAgentSelect(preferredAgentId, preferredModelId);
        renderSettings();
    }

    function syncAgentDefaultModelOptionsFromForm() {
        const selectedModelId = String(elements.agentDefaultModelSelect.value || '').trim();
        const models = parseLineList(elements.agentModelsTextarea.value);
        renderAgentDefaultModelOptions(models, selectedModelId);
    }

    function getStatusClass(record) {
        if (!record) {
            return '';
        }
        if (record.status === 'completed') {
            return 'status-completed';
        }
        if (record.status === 'failed') {
            return 'status-failed';
        }
        if (record.runtime_state === 'running') {
            return 'status-running';
        }
        return 'status-queued';
    }

    function renderStatusPill(record) {
        return `<span class="status-pill ${getStatusClass(record)}">${escapeHtml(record.status_label)}</span>`;
    }

    function renderPagination(pagination) {
        const info = pagination || {};
        state.page = Number(info.page) || 1;
        state.pageSize = Number(info.page_size) || state.pageSize || 50;
        state.totalPages = Number(info.total_pages) || 1;
        state.totalRecords = Number(info.total) || 0;

        elements.pageInfo.textContent = `第 ${state.page} 页 / 共 ${state.totalPages} 页`;
        elements.totalCount.textContent = `共 ${state.totalRecords} 条`;
        elements.prevBtn.classList.toggle('disabled', !info.has_prev);
        elements.nextBtn.classList.toggle('disabled', !info.has_next);
        elements.pageJumpInput.max = String(state.totalPages);
        elements.pageJumpInput.value = String(state.page);
        elements.pageSizeSelect.value = String(state.pageSize);
        elements.tableFooter.style.display = 'flex';
    }

    function renderRecords(records) {
        state.records = records;

        if (!records.length) {
            elements.recordsTableBody.innerHTML = '<tr><td colspan="6" class="empty-row">暂无检视记录。</td></tr>';
            return;
        }

        elements.recordsTableBody.innerHTML = records.map(function(record) {
            const mrTitle = record.title || record.mr_url;
            return `
                <tr>
                    <td class="col-mr">
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(mrTitle)}</div>
                            <a class="record-link" href="${escapeHtml(record.mr_url)}" target="_blank" rel="noreferrer">${escapeHtml(record.mr_url)}</a>
                        </div>
                    </td>
                    <td class="col-hub">${escapeHtml(record.hub_id)}</td>
                    <td class="col-agent">
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(record.agent_id)}</div>
                            <div class="record-subtitle">${escapeHtml(record.model_id)}</div>
                        </div>
                    </td>
                    <td class="col-status">${renderStatusPill(record)}</td>
                    <td class="col-time">
                        <div class="record-time">创建: ${escapeHtml(formatDate(record.created_at))}</div>
                        <div class="record-time">开始: ${escapeHtml(formatDate(record.started_at))}</div>
                    </td>
                    <td class="col-actions">
                        <div class="record-actions">
                            <button type="button" class="table-action-button" data-view-review-id="${record.id}">详情</button>
                            <button type="button" class="table-action-button" data-prefill-review-id="${record.id}">重试</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function refreshReviews() {
        const params = new URLSearchParams({
            page: String(state.page),
            page_size: String(state.pageSize)
        });
        const payload = await requestJson(`/api/reviews?${params.toString()}`);
        renderRecords(payload.records || []);
        renderPagination(payload.pagination || {});

        if (state.openDetailId != null && !elements.detailModal.hidden) {
            await loadDetail(state.openDetailId, true);
        }
    }

    function openDetailModal() {
        elements.detailModal.hidden = false;
        document.body.classList.add('modal-open');
    }

    function closeDetailModal() {
        state.openDetailId = null;
        state.openDetailRecord = null;
        elements.detailModal.hidden = true;
        elements.detailContent.hidden = true;
        document.body.classList.remove('modal-open');
    }

    function renderDetail(detail) {
        state.openDetailId = detail.id;
        state.openDetailRecord = detail;
        elements.detailStatusPill.className = `status-pill ${getStatusClass(detail)}`;
        elements.detailStatusPill.textContent = detail.status_label;
        elements.detailContent.hidden = false;

        elements.detailMrUrl.textContent = detail.mr_url || '-';
        elements.detailMrUrl.href = detail.mr_url || '#';
        elements.detailHub.textContent = detail.hub_id || '-';
        elements.detailAgent.textContent = detail.agent_id || '-';
        elements.detailModel.textContent = detail.model_id || '-';
        elements.detailSourceBranch.textContent = detail.source_branch || '-';
        elements.detailTargetBranch.textContent = detail.target_branch || '-';
        elements.detailCreatedAt.textContent = formatDate(detail.created_at);
        elements.detailStartedAt.textContent = formatDate(detail.started_at);
        elements.detailFinishedAt.textContent = formatDate(detail.finished_at);
        elements.detailCommand.textContent = detail.command_line || '-';
        elements.detailLogs.textContent = (detail.logs || []).map(function(item) {
            return stripTerminalControlSequences(item.line);
        }).join('\n') || '-';

        openDetailModal();
    }

    async function loadDetail(reviewId, silent) {
        try {
            const payload = await requestJson(`/api/reviews/${reviewId}`);
            renderDetail(payload);
        } catch (error) {
            if (!silent) {
                throw error;
            }
        }
    }

    function prefillReviewForm(record) {
        if (!record || !record.mr_url) {
            showToast('无法回填 MR 地址。', 'error');
            return;
        }

        elements.mrUrlInput.value = record.mr_url;

        if (record.hub_id && Array.from(elements.hubSelect.options).some(function(option) { return option.value === record.hub_id; })) {
            elements.hubSelect.value = record.hub_id;
        }
        syncReviewFormQuickActions();

        if (!elements.detailModal.hidden) {
            closeDetailModal();
        }

        setActivePageTab('review');
        window.requestAnimationFrame(function() {
            elements.mrUrlInput.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            elements.mrUrlInput.focus();
        });
    }

    function jumpToPage(force) {
        const page = Number.parseInt(elements.pageJumpInput.value, 10);
        if (Number.isNaN(page)) {
            if (force) {
                elements.pageJumpInput.value = String(state.page);
            }
            return;
        }

        const targetPage = Math.min(state.totalPages, Math.max(1, page));
        if (targetPage === state.page) {
            elements.pageJumpInput.value = String(state.page);
            return;
        }

        state.page = targetPage;
        refreshReviews().catch(function(error) {
            showToast(error.message || String(error), 'error');
        });
    }

    function queueJumpToPage() {
        if (state.jumpDebounceTimer) {
            window.clearTimeout(state.jumpDebounceTimer);
        }
        state.jumpDebounceTimer = window.setTimeout(function() {
            jumpToPage(false);
        }, 350);
    }

    function collectAgentSettingsPayload() {
        const models = parseLineList(elements.agentModelsTextarea.value);
        return {
            list_models_command: String(elements.agentListModelsCommandInput.value || '').trim(),
            review_command: String(elements.agentReviewCommandInput.value || '').trim(),
            models: models,
            default_model_id: String(elements.agentDefaultModelSelect.value || '').trim(),
            extra_env: parseJsonObject(elements.agentExtraEnvTextarea.value, 'extra_env'),
            command_shell: (function() {
                const executable = String(elements.agentCommandShellExecutableInput.value || '').trim();
                const args = parseLineList(elements.agentCommandShellArgsInput.value);
                if (!executable) {
                    return null;
                }
                return {
                    executable: executable,
                    args: args
                };
            })()
        };
    }

    function collectHubSettingsPayload() {
        return {
            type: String(elements.hubTypeSelect.value || '').trim(),
            web_base_url: String(elements.hubWebBaseUrlInput.value || '').trim(),
            api_base_url: String(elements.hubApiBaseUrlInput.value || '').trim(),
            private_token: String(elements.hubPrivateTokenInput.value || '').trim(),
            clone_url_preference: String(elements.hubClonePreferenceSelect.value || 'http').trim(),
            timeout_seconds: String(elements.hubTimeoutInput.value || '').trim() || 20,
            verify_ssl: Boolean(elements.hubVerifySslInput.checked)
        };
    }

    async function saveAgentSettings(options) {
        const agentId = state.activeAgentSettingsId;
        if (!agentId) {
            throw new Error('请先选择智能体。');
        }

        const payload = collectAgentSettingsPayload();
        const currentReviewAgentId = String(elements.agentSelect.value || '');
        const currentReviewHubId = String(elements.hubSelect.value || '');
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(agentId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        await reloadPageState({
            agentId: currentReviewAgentId,
            hubId: currentReviewHubId,
            modelId: currentReviewAgentId === agentId ? String(payload.default_model_id || '') : currentReviewModelId,
            activeAgentSettingsId: agentId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        if (!options || !options.silent) {
            showToast('智能体配置已保存。', 'success');
        }

        return response;
    }

    async function refreshAgentModelsFromSettings() {
        const agentId = state.activeAgentSettingsId;
        if (!agentId) {
            throw new Error('请先选择智能体。');
        }

        const currentReviewAgentId = String(elements.agentSelect.value || '');
        const currentReviewHubId = String(elements.hubSelect.value || '');
        await saveAgentSettings({ silent: true });
        const response = await requestJson(`/api/agents/${encodeURIComponent(agentId)}/models/refresh`, {
            method: 'POST'
        });

        await reloadPageState({
            activeAgentSettingsId: agentId,
            activeHubSettingsId: state.activeHubSettingsId,
            agentId: currentReviewAgentId,
            hubId: currentReviewHubId,
            modelId: currentReviewAgentId === agentId
                ? String((response.config && response.config.default_model) || '')
                : String(elements.modelSelect.value || '')
        });

        const modelCount = Array.isArray(response.models) ? response.models.length : 0;
        showToast(`已刷新 ${modelCount} 个模型。`, 'success');
    }

    async function saveHubSettings() {
        const hubId = state.activeHubSettingsId;
        if (!hubId) {
            throw new Error('请先选择平台。');
        }

        const payload = collectHubSettingsPayload();
        const currentReviewAgentId = String(elements.agentSelect.value || '');
        const currentReviewHubId = String(elements.hubSelect.value || '');
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(hubId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        await reloadPageState({
            agentId: currentReviewAgentId,
            hubId: currentReviewHubId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: hubId
        });

        showToast('平台配置已保存。', 'success');
        return response;
    }

    async function setDefaultAgentFromSettings() {
        const agentId = state.activeAgentSettingsId;
        if (!agentId) {
            throw new Error('请先选择智能体。');
        }

        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(agentId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            agentId: response.agent_id || agentId,
            modelId: '',
            activeAgentSettingsId: agentId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        showToast('默认智能体已更新。', 'success');
    }

    async function setDefaultHubFromSettings() {
        const hubId = state.activeHubSettingsId;
        if (!hubId) {
            throw new Error('请先选择平台。');
        }

        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(hubId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: response.hub_id || hubId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: hubId
        });

        showToast('默认平台已更新。', 'success');
    }

    async function setDefaultHubFromReviewForm() {
        const hubId = String(elements.hubSelect.value || '').trim();
        const agentId = String(elements.agentSelect.value || '').trim();
        const modelId = String(elements.modelSelect.value || '').trim();
        if (!hubId) {
            throw new Error('请先选择平台。');
        }

        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(hubId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: response.hub_id || hubId,
            agentId: agentId,
            modelId: modelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        showToast('默认平台已更新。', 'success');
    }

    async function setDefaultAgentFromReviewForm() {
        const hubId = String(elements.hubSelect.value || '').trim();
        const agentId = String(elements.agentSelect.value || '').trim();
        const modelId = String(elements.modelSelect.value || '').trim();
        if (!agentId) {
            throw new Error('请先选择 Agent。');
        }

        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(agentId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: hubId,
            agentId: response.agent_id || agentId,
            modelId: modelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        showToast('默认 Agent 已更新。', 'success');
    }

    async function setDefaultModelFromReviewForm() {
        const hubId = String(elements.hubSelect.value || '').trim();
        const agentId = String(elements.agentSelect.value || '').trim();
        const modelId = String(elements.modelSelect.value || '').trim();
        if (!agentId) {
            throw new Error('请先选择 Agent。');
        }
        if (!modelId) {
            throw new Error('请先选择模型。');
        }

        await requestJson(`/api/agents/${encodeURIComponent(agentId)}/default-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_id: modelId
            })
        });

        await reloadPageState({
            hubId: hubId,
            agentId: agentId,
            modelId: modelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        showToast('默认模型已更新。', 'success');
    }

    async function refreshAgentModelsFromReviewForm() {
        const hubId = String(elements.hubSelect.value || '').trim();
        const agentId = String(elements.agentSelect.value || '').trim();
        const modelId = String(elements.modelSelect.value || '').trim();
        if (!agentId) {
            throw new Error('请先选择 Agent。');
        }

        const response = await requestJson(`/api/agents/${encodeURIComponent(agentId)}/models/refresh`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: hubId,
            agentId: agentId,
            modelId: modelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: state.activeHubSettingsId
        });

        const modelCount = Array.isArray(response.models) ? response.models.length : 0;
        showToast(`已刷新 ${modelCount} 个模型。`, 'success');
    }

    async function submitReview(event) {
        event.preventDefault();

        const payload = {
            mr_url: String(elements.mrUrlInput.value || '').trim(),
            hub_id: String(elements.hubSelect.value || '').trim(),
            agent_id: String(elements.agentSelect.value || '').trim(),
            model_id: String(elements.modelSelect.value || '').trim()
        };

        if (!payload.mr_url) {
            showToast('请输入 MR 地址。', 'error');
            elements.mrUrlInput.focus();
            return;
        }

        if (!payload.model_id) {
            showToast('请选择模型。', 'error');
            elements.modelSelect.focus();
            return;
        }

        await runWithBusyButton(elements.submitButton, '提交中...', async function() {
            await requestJson('/api/reviews', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            showToast('检视任务已加入队列。', 'success');
            elements.reviewForm.reset();
            populateHubSelect('');
            populateAgentSelect('', '');
            state.page = 1;
            await refreshReviews();
        });
    }

    function bindEvents() {
        elements.pageTabButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                setActivePageTab(button.getAttribute('data-page-tab-target'));
            });
        });

        elements.settingsTabButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                setActiveSettingsTab(button.getAttribute('data-settings-tab-target'));
            });
        });

        elements.hubSelect.addEventListener('change', function() {
            syncReviewFormQuickActions();
        });

        elements.agentSelect.addEventListener('change', function() {
            updateModelSuggestions('');
        });

        elements.modelSelect.addEventListener('change', function() {
            syncReviewFormQuickActions();
        });

        elements.hubSetDefaultQuickButton.addEventListener('click', function() {
            runWithBusyButton(elements.hubSetDefaultQuickButton, '更新中...', function() {
                return setDefaultHubFromReviewForm();
            }).then(function() {
                syncReviewFormQuickActions();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.agentSetDefaultQuickButton.addEventListener('click', function() {
            runWithBusyButton(elements.agentSetDefaultQuickButton, '更新中...', function() {
                return setDefaultAgentFromReviewForm();
            }).then(function() {
                syncReviewFormQuickActions();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.modelSetDefaultQuickButton.addEventListener('click', function() {
            runWithBusyButton(elements.modelSetDefaultQuickButton, '更新中...', function() {
                return setDefaultModelFromReviewForm();
            }).then(function() {
                syncReviewFormQuickActions();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.modelRefreshQuickButton.addEventListener('click', function() {
            runWithBusyButton(elements.modelRefreshQuickButton, '刷新中...', function() {
                return refreshAgentModelsFromReviewForm();
            }).then(function() {
                syncReviewFormQuickActions();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.reviewForm.addEventListener('submit', function(event) {
            submitReview(event).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.queueRefreshButton.addEventListener('click', function() {
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.autoRefreshToggleButton.addEventListener('click', function() {
            setAutoRefresh(!state.autoRefreshEnabled);
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.prevBtn.addEventListener('click', function() {
            if (state.page <= 1) {
                return;
            }
            state.page -= 1;
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.nextBtn.addEventListener('click', function() {
            if (state.page >= state.totalPages) {
                return;
            }
            state.page += 1;
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        [elements.prevBtn, elements.nextBtn].forEach(function(node) {
            node.addEventListener('keydown', function(event) {
                if (event.key !== 'Enter' && event.key !== ' ') {
                    return;
                }
                event.preventDefault();
                node.click();
            });
        });

        elements.pageJumpInput.addEventListener('input', queueJumpToPage);
        elements.pageJumpInput.addEventListener('blur', function() {
            jumpToPage(true);
        });
        elements.pageJumpInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                jumpToPage(true);
            }
        });

        elements.pageSizeSelect.addEventListener('change', function() {
            const nextPageSize = Number.parseInt(elements.pageSizeSelect.value, 10);
            if (!Number.isFinite(nextPageSize) || nextPageSize <= 0 || nextPageSize === state.pageSize) {
                return;
            }

            state.pageSize = nextPageSize;
            state.page = 1;
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.recordsTableBody.addEventListener('click', function(event) {
            const viewButton = event.target.closest('[data-view-review-id]');
            if (viewButton) {
                const reviewId = Number(viewButton.getAttribute('data-view-review-id'));
                loadDetail(reviewId).catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
                return;
            }

            const prefillButton = event.target.closest('[data-prefill-review-id]');
            if (prefillButton) {
                const reviewId = Number(prefillButton.getAttribute('data-prefill-review-id'));
                const record = state.records.find(function(item) {
                    return Number(item.id) === reviewId;
                }) || null;
                prefillReviewForm(record);
            }
        });

        elements.detailPrefillButton.addEventListener('click', function() {
            if (!state.openDetailRecord) {
                return;
            }
            prefillReviewForm(state.openDetailRecord);
        });

        document.querySelectorAll('[data-close-detail-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeDetailModal();
            });
        });

        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && !elements.detailModal.hidden) {
                closeDetailModal();
            }
        });

        elements.agentSettingsList.addEventListener('click', function(event) {
            const button = event.target.closest('[data-agent-settings-id]');
            if (!button) {
                return;
            }
            state.activeAgentSettingsId = button.getAttribute('data-agent-settings-id') || '';
            renderAgentSettingsList();
            renderAgentSettingsEditor();
        });

        elements.hubSettingsList.addEventListener('click', function(event) {
            const button = event.target.closest('[data-hub-settings-id]');
            if (!button) {
                return;
            }
            state.activeHubSettingsId = button.getAttribute('data-hub-settings-id') || '';
            renderHubSettingsList();
            renderHubSettingsEditor();
        });

        elements.agentModelsTextarea.addEventListener('input', function() {
            syncAgentDefaultModelOptionsFromForm();
        });

        elements.hubTypeSelect.addEventListener('change', function() {
            elements.hubTypePill.textContent = `类型: ${elements.hubTypeSelect.value || '-'}`;
        });

        elements.agentSettingsForm.addEventListener('submit', function(event) {
            event.preventDefault();
            runWithBusyButton(elements.agentSaveButton, '保存中...', function() {
                return saveAgentSettings();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.agentRefreshModelsButton.addEventListener('click', function() {
            runWithBusyButton(elements.agentRefreshModelsButton, '刷新中...', function() {
                return refreshAgentModelsFromSettings();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.agentSetDefaultButton.addEventListener('click', function() {
            runWithBusyButton(elements.agentSetDefaultButton, '更新中...', function() {
                return setDefaultAgentFromSettings();
            }).then(function() {
                renderAgentSettingsEditor();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.hubSettingsForm.addEventListener('submit', function(event) {
            event.preventDefault();
            runWithBusyButton(elements.hubSaveButton, '保存中...', function() {
                return saveHubSettings();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.hubSetDefaultButton.addEventListener('click', function() {
            runWithBusyButton(elements.hubSetDefaultButton, '更新中...', function() {
                return setDefaultHubFromSettings();
            }).then(function() {
                renderHubSettingsEditor();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });
    }

    async function bootstrap() {
        if (window.initThemeToggle) {
            window.initThemeToggle();
        }

        bindEvents();
        setActivePageTab(state.activePageTab);
        setActiveSettingsTab(state.activeSettingsTab);
        setAutoRefresh(false);
        await reloadPageState();
        await refreshReviews();
    }

    document.addEventListener('DOMContentLoaded', function() {
        try {
            cacheElements();
            bootstrap().catch(function(error) {
                showToast(error.message || String(error), 'error');
                console.error(error);
            });
        } catch (error) {
            console.error(error);
        }
    });
})();
