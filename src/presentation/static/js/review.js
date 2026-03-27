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
        settingsTables: {
            agents: {
                page: 1,
                pageSize: 50,
                totalPages: 1,
                totalRecords: 0,
                jumpDebounceTimer: null
            },
            hubs: {
                page: 1,
                pageSize: 50,
                totalPages: 1,
                totalRecords: 0,
                jumpDebounceTimer: null
            }
        },
        activePageTab: 'review',
        activeSettingsTab: 'agents',
        activeAgentSettingsId: '',
        activeHubSettingsId: '',
        editingAgentSettingsId: '',
        editingHubSettingsId: '',
        isAgentSettingsModalOpen: false,
        isHubSettingsModalOpen: false,
        isAgentFetchModelsModalOpen: false,
        isAgentModelListModalOpen: false,
        pendingReviewCancelId: '',
        pendingReviewCancelSource: '',
        cancelingReviewCancelId: '',
        pendingReviewDeleteId: '',
        pendingReviewDeleteSource: '',
        deletingReviewDeleteId: '',
        pendingSettingsDeleteKind: '',
        pendingSettingsDeleteId: '',
        deletingSettingsDeleteKey: '',
        fetchedAgentModelCandidates: [],
        fetchedAgentModelSelection: new Set(),
        fetchedAgentModelExistingSelection: new Set(),
        viewingAgentModelListId: '',
        viewingAgentModelIds: [],
        viewingAgentModelDefaultId: ''
    };

    const elements = {};
    const COPY_LINK_ICON_MARKUP = `
        <svg class="copy-link-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <rect x="9" y="9" width="11" height="11" rx="2.25"></rect>
            <path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"></path>
        </svg>
    `.trim();

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

        elements.agentCreateButton = document.getElementById('agentCreateButton');
        elements.agentSettingsList = document.getElementById('agentSettingsList');
        elements.agentTableFooter = document.getElementById('agentTableFooter');
        elements.agentPrevBtn = document.getElementById('agentPrevBtn');
        elements.agentNextBtn = document.getElementById('agentNextBtn');
        elements.agentPageInfo = document.getElementById('agentPageInfo');
        elements.agentPageJumpInput = document.getElementById('agentPageJumpInput');
        elements.agentPageSizeSelect = document.getElementById('agentPageSizeSelect');
        elements.agentTotalCount = document.getElementById('agentTotalCount');
        elements.agentSettingsModal = document.getElementById('agentSettingsModal');
        elements.agentSettingsForm = document.getElementById('agentSettingsForm');
        elements.agentSettingsTitle = document.getElementById('agentSettingsTitle');
        elements.agentSettingsId = document.getElementById('agentSettingsId');
        elements.agentListModelsCommandInput = document.getElementById('agentListModelsCommandInput');
        elements.agentReviewCommandInput = document.getElementById('agentReviewCommandInput');
        elements.agentDefaultModelSelect = document.getElementById('agentDefaultModelSelect');
        elements.agentModelsTextarea = document.getElementById('agentModelsTextarea');
        elements.agentExtraEnvField = document.getElementById('agentExtraEnvField');
        elements.agentExtraEnvList = document.getElementById('agentExtraEnvList');
        elements.agentAddEnvRowButton = document.getElementById('agentAddEnvRowButton');
        elements.agentRefreshModelsButton = document.getElementById('agentRefreshModelsButton');
        elements.agentSaveButton = document.getElementById('agentSaveButton');
        elements.agentFetchModelsModal = document.getElementById('agentFetchModelsModal');
        elements.agentFetchModelsTitle = document.getElementById('agentFetchModelsTitle');
        elements.agentFetchModelsSubtitle = document.getElementById('agentFetchModelsSubtitle');
        elements.agentFetchModelSearchInput = document.getElementById('agentFetchModelSearchInput');
        elements.agentFetchModelSummary = document.getElementById('agentFetchModelSummary');
        elements.agentFetchModelSelectAllCheckbox = document.getElementById('agentFetchModelSelectAllCheckbox');
        elements.agentFetchModelListBody = document.getElementById('agentFetchModelListBody');
        elements.agentApplyFetchedModelsButton = document.getElementById('agentApplyFetchedModelsButton');
        elements.agentModelListModal = document.getElementById('agentModelListModal');
        elements.agentModelListTitle = document.getElementById('agentModelListTitle');
        elements.agentModelListSubtitle = document.getElementById('agentModelListSubtitle');
        elements.agentModelListSearchInput = document.getElementById('agentModelListSearchInput');
        elements.agentModelListSummary = document.getElementById('agentModelListSummary');
        elements.agentModelListBody = document.getElementById('agentModelListBody');

        elements.hubCreateButton = document.getElementById('hubCreateButton');
        elements.hubSettingsList = document.getElementById('hubSettingsList');
        elements.hubTableFooter = document.getElementById('hubTableFooter');
        elements.hubPrevBtn = document.getElementById('hubPrevBtn');
        elements.hubNextBtn = document.getElementById('hubNextBtn');
        elements.hubPageInfo = document.getElementById('hubPageInfo');
        elements.hubPageJumpInput = document.getElementById('hubPageJumpInput');
        elements.hubPageSizeSelect = document.getElementById('hubPageSizeSelect');
        elements.hubTotalCount = document.getElementById('hubTotalCount');
        elements.hubSettingsModal = document.getElementById('hubSettingsModal');
        elements.hubSettingsForm = document.getElementById('hubSettingsForm');
        elements.hubSettingsTitle = document.getElementById('hubSettingsTitle');
        elements.hubSettingsId = document.getElementById('hubSettingsId');
        elements.hubTypeSelect = document.getElementById('hubTypeSelect');
        elements.hubWebBaseUrlInput = document.getElementById('hubWebBaseUrlInput');
        elements.hubApiBaseUrlInput = document.getElementById('hubApiBaseUrlInput');
        elements.hubPrivateTokenInput = document.getElementById('hubPrivateTokenInput');
        elements.hubClonePreferenceSelect = document.getElementById('hubClonePreferenceSelect');
        elements.hubTimeoutInput = document.getElementById('hubTimeoutInput');
        elements.hubVerifySslInput = document.getElementById('hubVerifySslInput');
        elements.hubSettingsHint = document.getElementById('hubSettingsHint');
        elements.hubSaveButton = document.getElementById('hubSaveButton');
        elements.hubApiBaseUrlRequiredMark = document.getElementById('hubApiBaseUrlRequiredMark');
        elements.settingsDeletePopover = document.getElementById('settingsDeletePopover');
        elements.settingsDeleteConfirmText = document.getElementById('settingsDeleteConfirmText');
        elements.settingsDeleteCancelButton = document.getElementById('settingsDeleteCancelButton');
        elements.settingsDeleteConfirmButton = document.getElementById('settingsDeleteConfirmButton');
        elements.reviewCancelPopover = document.getElementById('reviewCancelPopover');
        elements.reviewCancelConfirmText = document.getElementById('reviewCancelConfirmText');
        elements.reviewCancelCancelButton = document.getElementById('reviewCancelCancelButton');
        elements.reviewCancelConfirmButton = document.getElementById('reviewCancelConfirmButton');
        elements.reviewDeletePopover = document.getElementById('reviewDeletePopover');
        elements.reviewDeleteConfirmText = document.getElementById('reviewDeleteConfirmText');
        elements.reviewDeleteCancelButton = document.getElementById('reviewDeleteCancelButton');
        elements.reviewDeleteConfirmButton = document.getElementById('reviewDeleteConfirmButton');

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
        elements.detailCancelButton = document.getElementById('detailCancelButton');
        elements.detailDeleteButton = document.getElementById('detailDeleteButton');
        elements.detailPrefillButton = document.getElementById('detailPrefillButton');
        elements.detailStatusPill = document.getElementById('detailStatusPill');
        elements.detailContent = document.getElementById('detailContent');
        elements.detailMrUrl = document.getElementById('detailMrUrl');
        elements.detailMrUrlCopyButton = document.getElementById('detailMrUrlCopyButton');
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

    function updateCopyButtonAccessibility(button, prefix) {
        if (!button) {
            return;
        }

        const label = button.getAttribute('data-copy-label') || '内容';
        const actionLabel = `${prefix}${label}`;
        button.setAttribute('title', actionLabel);
        button.setAttribute('aria-label', actionLabel);
    }

    function resetCopyButtonState(button) {
        if (!button) {
            return;
        }

        if (button._copyFeedbackTimer) {
            window.clearTimeout(button._copyFeedbackTimer);
            button._copyFeedbackTimer = null;
        }

        button.classList.remove('is-copied');
        updateCopyButtonAccessibility(button, '复制 ');
    }

    function showCopyButtonSuccess(button) {
        if (!button) {
            return;
        }

        resetCopyButtonState(button);
        button.classList.add('is-copied');
        updateCopyButtonAccessibility(button, '已复制 ');
        button._copyFeedbackTimer = window.setTimeout(function() {
            resetCopyButtonState(button);
        }, 1400);
    }

    async function copyTextToClipboard(value) {
        const text = String(value || '').trim();
        if (!text) {
            throw new Error('没有可复制的 MR 地址。');
        }

        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
            try {
                await navigator.clipboard.writeText(text);
                return;
            } catch (error) {
                // Fall back to execCommand for environments without Clipboard API permissions.
            }
        }

        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', 'readonly');
        textarea.style.position = 'fixed';
        textarea.style.top = '-9999px';
        textarea.style.left = '-9999px';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        textarea.setSelectionRange(0, textarea.value.length);

        let copied = false;
        try {
            copied = Boolean(document.execCommand && document.execCommand('copy'));
        } finally {
            textarea.remove();
        }

        if (!copied) {
            throw new Error('复制失败，请手动复制 MR 地址。');
        }
    }

    async function copyFromButton(button) {
        if (!button) {
            return;
        }

        try {
            await copyTextToClipboard(button.getAttribute('data-copy-text') || '');
            showCopyButtonSuccess(button);
            showToast(`${button.getAttribute('data-copy-label') || '内容'}已复制。`, 'success');
        } catch (error) {
            resetCopyButtonState(button);
            showToast(error.message || String(error), 'error');
        }
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

    async function runWithBusyButton(button, busyText, action, options) {
        if (!button || button.disabled || button.classList.contains('is-loading')) {
            return Promise.resolve();
        }
        const config = options || {};
        const preserveLabel = Boolean(config.preserveLabel);
        const lockWidth = !preserveLabel && config.lockWidth !== false;
        const originalText = button.textContent;
        const originalWidth = button.style.width;
        const measuredWidth = button.getBoundingClientRect().width;
        if (lockWidth && measuredWidth > 0) {
            button.style.width = `${Math.ceil(measuredWidth)}px`;
        }
        button.disabled = true;
        button.classList.add('is-loading');
        button.setAttribute('aria-busy', 'true');
        if (!preserveLabel) {
            button.textContent = busyText;
        }

        try {
            return await action();
        } finally {
            button.disabled = false;
            button.classList.remove('is-loading');
            button.removeAttribute('aria-busy');
            if (!preserveLabel) {
                button.textContent = originalText;
            }
            if (lockWidth) {
                button.style.width = originalWidth;
            }
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

    function getSettingsDeleteKey(kind, id) {
        const normalizedKind = kind === 'hub' ? 'hub' : 'agent';
        const normalizedId = String(id || '').trim();
        return normalizedId ? `${normalizedKind}:${normalizedId}` : '';
    }

    function getPendingSettingsDeleteKey() {
        return getSettingsDeleteKey(state.pendingSettingsDeleteKind, state.pendingSettingsDeleteId);
    }

    function getPendingReviewCancelKey() {
        return String(state.pendingReviewCancelId || '').trim();
    }

    function getPendingReviewDeleteKey() {
        return String(state.pendingReviewDeleteId || '').trim();
    }

    function getReviewRecordById(reviewId) {
        const normalizedId = String(reviewId || '').trim();
        if (!normalizedId) {
            return null;
        }

        if (state.openDetailRecord && String(state.openDetailRecord.id) === normalizedId) {
            return state.openDetailRecord;
        }

        return state.records.find(function(record) {
            return String(record.id) === normalizedId;
        }) || null;
    }

    function getReviewCancelTrigger(reviewId, source) {
        const normalizedId = String(reviewId || '').trim();
        if (!normalizedId) {
            return null;
        }

        if (source === 'detail') {
            if (!elements.detailCancelButton || elements.detailCancelButton.hidden || elements.detailCancelButton.disabled) {
                return null;
            }
            if (!state.openDetailRecord || String(state.openDetailRecord.id) !== normalizedId) {
                return null;
            }
            return elements.detailCancelButton;
        }

        return Array.from(document.querySelectorAll('[data-cancel-review-id]')).find(function(button) {
            return String(button.getAttribute('data-cancel-review-id') || '').trim() === normalizedId;
        }) || null;
    }

    function hideReviewCancelPopover() {
        if (!elements.reviewCancelPopover) {
            return;
        }

        elements.reviewCancelPopover.hidden = true;
        elements.reviewCancelPopover.style.removeProperty('top');
        elements.reviewCancelPopover.style.removeProperty('left');
        elements.reviewCancelPopover.style.removeProperty('--popover-arrow-left');
        elements.reviewCancelPopover.dataset.placement = 'bottom';
    }

    function syncReviewCancelTriggerState() {
        document.querySelectorAll('[data-cancel-review-id]').forEach(function(button) {
            button.classList.remove('is-active');
        });
        if (elements.detailCancelButton) {
            elements.detailCancelButton.classList.remove('is-active');
        }

        const trigger = getReviewCancelTrigger(state.pendingReviewCancelId, state.pendingReviewCancelSource);
        if (trigger) {
            trigger.classList.add('is-active');
        }
    }

    function syncReviewCancelPopover() {
        syncReviewCancelTriggerState();

        if (!elements.reviewCancelPopover || !elements.reviewCancelConfirmButton || !elements.reviewCancelConfirmText) {
            return;
        }

        const reviewId = getPendingReviewCancelKey();
        if (!reviewId) {
            hideReviewCancelPopover();
            return;
        }

        const trigger = getReviewCancelTrigger(reviewId, state.pendingReviewCancelSource);
        const record = getReviewRecordById(reviewId);
        if (!trigger || !record || !isReviewCancelable(record)) {
            state.pendingReviewCancelId = '';
            state.pendingReviewCancelSource = '';
            state.cancelingReviewCancelId = '';
            syncReviewCancelTriggerState();
            hideReviewCancelPopover();
            return;
        }

        const actionLabel = getCancelActionLabel(record);
        const actionText = actionLabel === '停止' ? '停止任务' : '取消任务';
        const isCanceling = state.cancelingReviewCancelId === reviewId;
        elements.reviewCancelConfirmText.textContent = `确认${actionText}？`;
        elements.reviewCancelConfirmButton.disabled = isCanceling;
        elements.reviewCancelConfirmButton.textContent = isCanceling ? `${actionLabel}中...` : '确认';

        elements.reviewCancelPopover.hidden = false;

        const triggerRect = trigger.getBoundingClientRect();
        const popoverRect = elements.reviewCancelPopover.getBoundingClientRect();
        const viewportPadding = 12;
        const offset = 10;
        const canPlaceBottom = triggerRect.bottom + offset + popoverRect.height <= window.innerHeight - viewportPadding;
        const shouldPlaceBottom = canPlaceBottom || triggerRect.top < popoverRect.height + viewportPadding + offset;
        const top = shouldPlaceBottom
            ? Math.min(window.innerHeight - popoverRect.height - viewportPadding, triggerRect.bottom + offset)
            : Math.max(viewportPadding, triggerRect.top - popoverRect.height - offset);
        const left = Math.min(
            window.innerWidth - popoverRect.width - viewportPadding,
            Math.max(viewportPadding, triggerRect.left + ((triggerRect.width - popoverRect.width) / 2))
        );
        const arrowLeft = Math.min(
            popoverRect.width - 18,
            Math.max(18, triggerRect.left + (triggerRect.width / 2) - left)
        );

        elements.reviewCancelPopover.dataset.placement = shouldPlaceBottom ? 'bottom' : 'top';
        elements.reviewCancelPopover.style.top = `${top}px`;
        elements.reviewCancelPopover.style.left = `${left}px`;
        elements.reviewCancelPopover.style.setProperty('--popover-arrow-left', `${arrowLeft}px`);
    }

    function openReviewCancelPopover(reviewId, source) {
        const normalizedId = String(reviewId || '').trim();
        const normalizedSource = source === 'detail' ? 'detail' : 'table';
        if (!normalizedId || state.cancelingReviewCancelId) {
            return;
        }

        if (state.pendingReviewCancelId === normalizedId && state.pendingReviewCancelSource === normalizedSource) {
            closeReviewCancelPopover();
            return;
        }

        closeReviewDeletePopover();
        closeSettingsDeletePopover();
        state.pendingReviewCancelId = normalizedId;
        state.pendingReviewCancelSource = normalizedSource;
        syncReviewCancelPopover();
    }

    function closeReviewCancelPopover(shouldSyncTriggers) {
        if (!getPendingReviewCancelKey() && !state.cancelingReviewCancelId) {
            return;
        }
        if (state.cancelingReviewCancelId) {
            return;
        }

        state.pendingReviewCancelId = '';
        state.pendingReviewCancelSource = '';
        hideReviewCancelPopover();
        if (shouldSyncTriggers !== false) {
            syncReviewCancelTriggerState();
        } else {
            document.querySelectorAll('[data-cancel-review-id]').forEach(function(button) {
                button.classList.remove('is-active');
            });
            if (elements.detailCancelButton) {
                elements.detailCancelButton.classList.remove('is-active');
            }
        }
    }

    function getReviewDeleteTrigger(reviewId, source) {
        const normalizedId = String(reviewId || '').trim();
        if (!normalizedId) {
            return null;
        }

        if (source === 'detail') {
            if (!elements.detailDeleteButton || elements.detailDeleteButton.hidden || elements.detailDeleteButton.disabled) {
                return null;
            }
            if (!state.openDetailRecord || String(state.openDetailRecord.id) !== normalizedId) {
                return null;
            }
            return elements.detailDeleteButton;
        }

        return Array.from(document.querySelectorAll('[data-delete-review-id]')).find(function(button) {
            return String(button.getAttribute('data-delete-review-id') || '').trim() === normalizedId;
        }) || null;
    }

    function hideReviewDeletePopover() {
        if (!elements.reviewDeletePopover) {
            return;
        }

        elements.reviewDeletePopover.hidden = true;
        elements.reviewDeletePopover.style.removeProperty('top');
        elements.reviewDeletePopover.style.removeProperty('left');
        elements.reviewDeletePopover.style.removeProperty('--popover-arrow-left');
        elements.reviewDeletePopover.dataset.placement = 'bottom';
    }

    function syncReviewDeleteTriggerState() {
        document.querySelectorAll('[data-delete-review-id]').forEach(function(button) {
            button.classList.remove('is-active');
        });
        if (elements.detailDeleteButton) {
            elements.detailDeleteButton.classList.remove('is-active');
        }

        const trigger = getReviewDeleteTrigger(state.pendingReviewDeleteId, state.pendingReviewDeleteSource);
        if (trigger) {
            trigger.classList.add('is-active');
        }
    }

    function syncReviewDeletePopover() {
        syncReviewDeleteTriggerState();

        if (!elements.reviewDeletePopover || !elements.reviewDeleteConfirmButton || !elements.reviewDeleteConfirmText) {
            return;
        }

        const reviewId = getPendingReviewDeleteKey();
        if (!reviewId) {
            hideReviewDeletePopover();
            return;
        }

        const trigger = getReviewDeleteTrigger(reviewId, state.pendingReviewDeleteSource);
        const record = getReviewRecordById(reviewId);
        if (!trigger || !record) {
            state.pendingReviewDeleteId = '';
            state.pendingReviewDeleteSource = '';
            state.deletingReviewDeleteId = '';
            syncReviewDeleteTriggerState();
            hideReviewDeletePopover();
            return;
        }

        const isDeleting = state.deletingReviewDeleteId === reviewId;
        const isRunning = isPendingReview(record) && ['running', 'canceling'].includes(String(record.runtime_state || ''));
        elements.reviewDeleteConfirmText.textContent = isRunning
            ? '确认删除任务？运行中的任务会先停止再删除。'
            : '确认删除任务？';
        elements.reviewDeleteConfirmButton.disabled = isDeleting;
        elements.reviewDeleteConfirmButton.textContent = isDeleting ? '删除中...' : '确认';

        elements.reviewDeletePopover.hidden = false;

        const triggerRect = trigger.getBoundingClientRect();
        const popoverRect = elements.reviewDeletePopover.getBoundingClientRect();
        const viewportPadding = 12;
        const offset = 10;
        const canPlaceBottom = triggerRect.bottom + offset + popoverRect.height <= window.innerHeight - viewportPadding;
        const shouldPlaceBottom = canPlaceBottom || triggerRect.top < popoverRect.height + viewportPadding + offset;
        const top = shouldPlaceBottom
            ? Math.min(window.innerHeight - popoverRect.height - viewportPadding, triggerRect.bottom + offset)
            : Math.max(viewportPadding, triggerRect.top - popoverRect.height - offset);
        const left = Math.min(
            window.innerWidth - popoverRect.width - viewportPadding,
            Math.max(viewportPadding, triggerRect.left + ((triggerRect.width - popoverRect.width) / 2))
        );
        const arrowLeft = Math.min(
            popoverRect.width - 18,
            Math.max(18, triggerRect.left + (triggerRect.width / 2) - left)
        );

        elements.reviewDeletePopover.dataset.placement = shouldPlaceBottom ? 'bottom' : 'top';
        elements.reviewDeletePopover.style.top = `${top}px`;
        elements.reviewDeletePopover.style.left = `${left}px`;
        elements.reviewDeletePopover.style.setProperty('--popover-arrow-left', `${arrowLeft}px`);
    }

    function openReviewDeletePopover(reviewId, source) {
        const normalizedId = String(reviewId || '').trim();
        const normalizedSource = source === 'detail' ? 'detail' : 'table';
        if (!normalizedId || state.deletingReviewDeleteId) {
            return;
        }

        if (state.pendingReviewDeleteId === normalizedId && state.pendingReviewDeleteSource === normalizedSource) {
            closeReviewDeletePopover();
            return;
        }

        closeReviewCancelPopover();
        closeSettingsDeletePopover();
        state.pendingReviewDeleteId = normalizedId;
        state.pendingReviewDeleteSource = normalizedSource;
        syncReviewDeletePopover();
    }

    function closeReviewDeletePopover(shouldSyncTriggers) {
        if (!getPendingReviewDeleteKey() && !state.deletingReviewDeleteId) {
            return;
        }
        if (state.deletingReviewDeleteId) {
            return;
        }

        state.pendingReviewDeleteId = '';
        state.pendingReviewDeleteSource = '';
        hideReviewDeletePopover();
        if (shouldSyncTriggers !== false) {
            syncReviewDeleteTriggerState();
        } else {
            document.querySelectorAll('[data-delete-review-id]').forEach(function(button) {
                button.classList.remove('is-active');
            });
            if (elements.detailDeleteButton) {
                elements.detailDeleteButton.classList.remove('is-active');
            }
        }
    }

    function getSettingsDeleteTrigger(kind, id) {
        const normalizedId = String(id || '').trim();
        if (!normalizedId) {
            return null;
        }

        const selector = kind === 'hub' ? '[data-delete-hub-id]' : '[data-delete-agent-id]';
        const attributeName = kind === 'hub' ? 'data-delete-hub-id' : 'data-delete-agent-id';
        return Array.from(document.querySelectorAll(selector)).find(function(button) {
            return String(button.getAttribute(attributeName) || '').trim() === normalizedId;
        }) || null;
    }

    function hideSettingsDeletePopover() {
        if (!elements.settingsDeletePopover) {
            return;
        }

        elements.settingsDeletePopover.hidden = true;
        elements.settingsDeletePopover.style.removeProperty('top');
        elements.settingsDeletePopover.style.removeProperty('left');
        elements.settingsDeletePopover.style.removeProperty('--popover-arrow-left');
        elements.settingsDeletePopover.dataset.placement = 'bottom';
    }

    function syncSettingsDeleteTriggerState() {
        document.querySelectorAll('[data-delete-agent-id], [data-delete-hub-id]').forEach(function(button) {
            button.classList.remove('is-active');
        });

        const trigger = getSettingsDeleteTrigger(state.pendingSettingsDeleteKind, state.pendingSettingsDeleteId);
        if (trigger) {
            trigger.classList.add('is-active');
        }
    }

    function syncSettingsDeletePopover() {
        syncSettingsDeleteTriggerState();

        if (!elements.settingsDeletePopover || !elements.settingsDeleteConfirmButton || !elements.settingsDeleteConfirmText) {
            return;
        }

        const kind = state.pendingSettingsDeleteKind;
        const id = String(state.pendingSettingsDeleteId || '').trim();
        const pendingKey = getPendingSettingsDeleteKey();
        if (!pendingKey) {
            hideSettingsDeletePopover();
            return;
        }

        const trigger = getSettingsDeleteTrigger(kind, id);
        if (!trigger) {
            state.pendingSettingsDeleteKind = '';
            state.pendingSettingsDeleteId = '';
            state.deletingSettingsDeleteKey = '';
            syncSettingsDeleteTriggerState();
            hideSettingsDeletePopover();
            return;
        }

        const label = kind === 'hub' ? '平台' : 'Agent';
        const isDeleting = state.deletingSettingsDeleteKey === pendingKey;
        elements.settingsDeleteConfirmText.textContent = `删除${label}“${id}”？`;
        elements.settingsDeleteConfirmButton.disabled = isDeleting;
        elements.settingsDeleteConfirmButton.textContent = isDeleting ? '删除中...' : '确认';

        elements.settingsDeletePopover.hidden = false;

        const triggerRect = trigger.getBoundingClientRect();
        const popoverRect = elements.settingsDeletePopover.getBoundingClientRect();
        const viewportPadding = 12;
        const offset = 10;
        const canPlaceBottom = triggerRect.bottom + offset + popoverRect.height <= window.innerHeight - viewportPadding;
        const shouldPlaceBottom = canPlaceBottom || triggerRect.top < popoverRect.height + viewportPadding + offset;
        const top = shouldPlaceBottom
            ? Math.min(window.innerHeight - popoverRect.height - viewportPadding, triggerRect.bottom + offset)
            : Math.max(viewportPadding, triggerRect.top - popoverRect.height - offset);
        const left = Math.min(
            window.innerWidth - popoverRect.width - viewportPadding,
            Math.max(viewportPadding, triggerRect.left + ((triggerRect.width - popoverRect.width) / 2))
        );
        const arrowLeft = Math.min(
            popoverRect.width - 18,
            Math.max(18, triggerRect.left + (triggerRect.width / 2) - left)
        );

        elements.settingsDeletePopover.dataset.placement = shouldPlaceBottom ? 'bottom' : 'top';
        elements.settingsDeletePopover.style.top = `${top}px`;
        elements.settingsDeletePopover.style.left = `${left}px`;
        elements.settingsDeletePopover.style.setProperty('--popover-arrow-left', `${arrowLeft}px`);
    }

    function openSettingsDeletePopover(kind, id) {
        const normalizedKind = kind === 'hub' ? 'hub' : 'agent';
        const normalizedId = String(id || '').trim();
        if (!normalizedId || state.deletingSettingsDeleteKey) {
            return;
        }

        if (state.pendingSettingsDeleteKind === normalizedKind && state.pendingSettingsDeleteId === normalizedId) {
            closeSettingsDeletePopover();
            return;
        }

        closeReviewCancelPopover();
        closeReviewDeletePopover();
        state.pendingSettingsDeleteKind = normalizedKind;
        state.pendingSettingsDeleteId = normalizedId;
        syncSettingsDeletePopover();
    }

    function closeSettingsDeletePopover(shouldSyncTriggers) {
        if (!getPendingSettingsDeleteKey() && !state.deletingSettingsDeleteKey) {
            return;
        }
        if (state.deletingSettingsDeleteKey) {
            return;
        }

        state.pendingSettingsDeleteKind = '';
        state.pendingSettingsDeleteId = '';
        hideSettingsDeletePopover();
        if (shouldSyncTriggers !== false) {
            syncSettingsDeleteTriggerState();
        } else {
            document.querySelectorAll('[data-delete-agent-id], [data-delete-hub-id]').forEach(function(button) {
                button.classList.remove('is-active');
            });
        }
    }

    function resetFetchedAgentModelPickerState() {
        state.fetchedAgentModelCandidates = [];
        state.fetchedAgentModelSelection = new Set();
        state.fetchedAgentModelExistingSelection = new Set();

        if (elements.agentFetchModelSearchInput) {
            elements.agentFetchModelSearchInput.value = '';
        }
        if (elements.agentFetchModelSummary) {
            elements.agentFetchModelSummary.textContent = '共拉取 0 个模型，已选 0 个';
        }
        if (elements.agentFetchModelSelectAllCheckbox) {
            elements.agentFetchModelSelectAllCheckbox.checked = false;
            elements.agentFetchModelSelectAllCheckbox.indeterminate = false;
            elements.agentFetchModelSelectAllCheckbox.disabled = true;
        }
        if (elements.agentFetchModelListBody) {
            elements.agentFetchModelListBody.innerHTML = '';
        }
    }

    function getFilteredFetchedAgentModels() {
        const query = String(elements.agentFetchModelSearchInput && elements.agentFetchModelSearchInput.value || '').trim().toLowerCase();
        if (!query) {
            return state.fetchedAgentModelCandidates.slice();
        }

        return state.fetchedAgentModelCandidates.filter(function(modelId) {
            return String(modelId || '').toLowerCase().includes(query);
        });
    }

    function updateFetchedAgentModelSummary(filteredCount) {
        if (!elements.agentFetchModelSummary) {
            return;
        }

        const totalCount = state.fetchedAgentModelCandidates.length;
        const visibleCount = Number.isFinite(filteredCount) ? filteredCount : totalCount;
        const selectedCount = state.fetchedAgentModelSelection.size;
        const existingCount = state.fetchedAgentModelExistingSelection.size;
        const visibleText = visibleCount !== totalCount ? `，当前显示 ${visibleCount} 个` : '';
        const existingText = existingCount ? `，其中 ${existingCount} 个原本已在清单中` : '';
        elements.agentFetchModelSummary.textContent = `共拉取 ${totalCount} 个模型${visibleText}，已选 ${selectedCount} 个${existingText}`;
    }

    function syncFetchedAgentModelSelectAllState(filteredModels) {
        if (!elements.agentFetchModelSelectAllCheckbox) {
            return;
        }

        const models = Array.isArray(filteredModels) ? filteredModels : getFilteredFetchedAgentModels();
        const visibleCount = models.length;
        const selectedVisibleCount = models.filter(function(modelId) {
            return state.fetchedAgentModelSelection.has(modelId);
        }).length;

        elements.agentFetchModelSelectAllCheckbox.disabled = visibleCount === 0;
        elements.agentFetchModelSelectAllCheckbox.indeterminate =
            visibleCount > 0 && selectedVisibleCount > 0 && selectedVisibleCount < visibleCount;
        elements.agentFetchModelSelectAllCheckbox.checked = visibleCount > 0 && selectedVisibleCount === visibleCount;
    }

    function renderFetchedAgentModelPicker() {
        if (!elements.agentFetchModelListBody) {
            return;
        }

        const filteredModels = getFilteredFetchedAgentModels();
        updateFetchedAgentModelSummary(filteredModels.length);
        syncFetchedAgentModelSelectAllState(filteredModels);

        if (!filteredModels.length) {
            elements.agentFetchModelListBody.innerHTML = '<div class="agent-fetch-model-empty">没有匹配的拉取模型</div>';
            return;
        }

        elements.agentFetchModelListBody.innerHTML = filteredModels.map(function(modelId) {
            const encodedModelId = encodeURIComponent(modelId);
            const isSelected = state.fetchedAgentModelSelection.has(modelId);
            const isExisting = state.fetchedAgentModelExistingSelection.has(modelId);
            return `
                <label class="agent-fetch-model-item${isSelected ? ' selected' : ''}">
                    <span class="agent-fetch-model-item-main">
                        <input
                            type="checkbox"
                            class="agent-fetch-model-checkbox"
                            data-fetched-agent-model="${encodedModelId}"
                            ${isSelected ? 'checked' : ''}
                        >
                        <span class="agent-fetch-model-item-name">${escapeHtml(modelId)}</span>
                    </span>
                    ${isExisting ? '<span class="agent-fetch-model-item-badge">已在当前清单</span>' : ''}
                </label>
            `;
        }).join('');
    }

    function openAgentFetchModelPicker(fetchedModels, agentId) {
        const normalizedFetchedModels = parseLineList((Array.isArray(fetchedModels) ? fetchedModels : []).join('\n'));
        const currentModels = parseLineList(elements.agentModelsTextarea ? elements.agentModelsTextarea.value : '');
        const fetchedModelSet = new Set(normalizedFetchedModels);
        const normalizedAgentId = String(agentId || state.editingAgentSettingsId || elements.agentSettingsId && elements.agentSettingsId.value || '').trim();

        state.fetchedAgentModelCandidates = normalizedFetchedModels;
        state.fetchedAgentModelExistingSelection = new Set(currentModels.filter(function(modelId) {
            return fetchedModelSet.has(modelId);
        }));
        state.fetchedAgentModelSelection = new Set(state.fetchedAgentModelExistingSelection);
        state.isAgentFetchModelsModalOpen = true;

        if (elements.agentFetchModelsTitle) {
            elements.agentFetchModelsTitle.textContent = normalizedAgentId ? `${normalizedAgentId} 模型` : '选择模型';
        }
        if (elements.agentFetchModelsSubtitle) {
            elements.agentFetchModelsSubtitle.hidden = true;
            elements.agentFetchModelsSubtitle.textContent = '';
        }
        if (elements.agentFetchModelSearchInput) {
            elements.agentFetchModelSearchInput.value = '';
        }

        renderFetchedAgentModelPicker();
        openModal(elements.agentFetchModelsModal);
        window.setTimeout(function() {
            if (elements.agentFetchModelSearchInput && state.isAgentFetchModelsModalOpen) {
                elements.agentFetchModelSearchInput.focus();
            }
        }, 0);
        return normalizedFetchedModels.length;
    }

    function closeAgentFetchModelsModal() {
        state.isAgentFetchModelsModalOpen = false;
        closeModal(elements.agentFetchModelsModal);
        resetFetchedAgentModelPickerState();
    }

    function resetAgentModelListViewerState() {
        state.viewingAgentModelListId = '';
        state.viewingAgentModelIds = [];
        state.viewingAgentModelDefaultId = '';

        if (elements.agentModelListSearchInput) {
            elements.agentModelListSearchInput.value = '';
        }
        if (elements.agentModelListSummary) {
            elements.agentModelListSummary.textContent = '共 0 个模型';
        }
        if (elements.agentModelListBody) {
            elements.agentModelListBody.innerHTML = '';
        }
    }

    function renderAgentModelListViewer() {
        if (!elements.agentModelListBody) {
            return;
        }

        const allModels = Array.isArray(state.viewingAgentModelIds) ? state.viewingAgentModelIds : [];
        const query = String(elements.agentModelListSearchInput && elements.agentModelListSearchInput.value || '').trim().toLowerCase();
        const filteredModels = query
            ? allModels.filter(function(modelId) {
                return String(modelId || '').toLowerCase().includes(query);
            })
            : allModels;

        if (elements.agentModelListSummary) {
            elements.agentModelListSummary.textContent = query
                ? `共 ${allModels.length} 个模型，筛选后 ${filteredModels.length} 个`
                : `共 ${allModels.length} 个模型`;
        }

        if (!filteredModels.length) {
            elements.agentModelListBody.innerHTML = '<div class="agent-model-list-empty">没有匹配的模型</div>';
            return;
        }

        const defaultModelId = String(state.viewingAgentModelDefaultId || '').trim();
        elements.agentModelListBody.innerHTML = filteredModels.map(function(modelId) {
            return `
                <div class="agent-model-list-item">
                    <span class="agent-model-list-item-name">${escapeHtml(modelId)}</span>
                    ${defaultModelId && defaultModelId === modelId ? '<span class="status-pill status-queued">默认</span>' : ''}
                </div>
            `;
        }).join('');
    }

    function openAgentModelListViewer(agentId) {
        const normalizedAgentId = String(agentId || '').trim();
        if (!normalizedAgentId) {
            return;
        }

        const agent = findSettingsAgent(normalizedAgentId);
        if (!agent) {
            showToast('未找到对应的 Agent 模型列表。', 'error');
            return;
        }

        const config = agent.config || {};
        const modelIds = collectAgentModelIds(agent);
        state.isAgentModelListModalOpen = true;
        state.viewingAgentModelListId = normalizedAgentId;
        state.viewingAgentModelIds = modelIds;
        state.viewingAgentModelDefaultId = String(config.default_model || agent.default_model_id || '').trim();

        if (elements.agentModelListTitle) {
            elements.agentModelListTitle.textContent = `${normalizedAgentId} 模型`;
        }
        if (elements.agentModelListSubtitle) {
            elements.agentModelListSubtitle.hidden = true;
            elements.agentModelListSubtitle.textContent = '';
        }
        if (elements.agentModelListSearchInput) {
            elements.agentModelListSearchInput.value = '';
        }

        renderAgentModelListViewer();
        openModal(elements.agentModelListModal);
        window.setTimeout(function() {
            if (elements.agentModelListSearchInput && state.isAgentModelListModalOpen) {
                elements.agentModelListSearchInput.focus();
            }
        }, 0);
    }

    function closeAgentModelListViewer() {
        state.isAgentModelListModalOpen = false;
        closeModal(elements.agentModelListModal);
        resetAgentModelListViewerState();
    }

    function toggleFetchedAgentModelSelection(modelId, checked, inputElement) {
        const normalizedModelId = String(modelId || '').trim();
        if (!normalizedModelId) {
            return;
        }

        if (checked) {
            state.fetchedAgentModelSelection.add(normalizedModelId);
        } else {
            state.fetchedAgentModelSelection.delete(normalizedModelId);
        }

        const itemElement = inputElement && inputElement.closest('.agent-fetch-model-item');
        if (itemElement) {
            itemElement.classList.toggle('selected', checked);
        }

        const filteredModels = getFilteredFetchedAgentModels();
        updateFetchedAgentModelSummary(filteredModels.length);
        syncFetchedAgentModelSelectAllState(filteredModels);
    }

    function toggleFilteredFetchedAgentModels(checked) {
        getFilteredFetchedAgentModels().forEach(function(modelId) {
            if (checked) {
                state.fetchedAgentModelSelection.add(modelId);
            } else {
                state.fetchedAgentModelSelection.delete(modelId);
            }
        });
        renderFetchedAgentModelPicker();
    }

    function applyFetchedAgentModelSelection() {
        const currentModels = parseLineList(elements.agentModelsTextarea ? elements.agentModelsTextarea.value : '');
        const currentModelSet = new Set(currentModels);
        const fetchedModelSet = new Set(state.fetchedAgentModelCandidates);
        const selectedFetchedModels = state.fetchedAgentModelCandidates.filter(function(modelId) {
            return state.fetchedAgentModelSelection.has(modelId);
        });
        const nextModels = [];
        const seen = new Set();

        currentModels.forEach(function(modelId) {
            if (fetchedModelSet.has(modelId) && !state.fetchedAgentModelSelection.has(modelId)) {
                return;
            }
            if (seen.has(modelId)) {
                return;
            }
            seen.add(modelId);
            nextModels.push(modelId);
        });

        selectedFetchedModels.forEach(function(modelId) {
            if (seen.has(modelId)) {
                return;
            }
            seen.add(modelId);
            nextModels.push(modelId);
        });

        const addedCount = selectedFetchedModels.filter(function(modelId) {
            return !currentModelSet.has(modelId);
        }).length;
        const removedCount = currentModels.filter(function(modelId) {
            return fetchedModelSet.has(modelId) && !state.fetchedAgentModelSelection.has(modelId);
        }).length;
        const currentDefaultModelId = String(elements.agentDefaultModelSelect && elements.agentDefaultModelSelect.value || '').trim();
        const nextDefaultModelId = nextModels.includes(currentDefaultModelId) ? currentDefaultModelId : '';

        elements.agentModelsTextarea.value = joinLineList(nextModels);
        renderAgentDefaultModelOptions(nextModels, nextDefaultModelId);
        elements.agentDefaultModelSelect.value = nextDefaultModelId;
        closeAgentFetchModelsModal();

        if (!addedCount && !removedCount) {
            showToast('模型列表未发生变化。', 'success');
            return;
        }

        showToast(`模型列表已更新，新增 ${addedCount} 个，移除 ${removedCount} 个。`, 'success');
    }

    function createAgentExtraEnvRow(key, value) {
        const row = document.createElement('div');
        row.className = 'settings-env-row';
        row.setAttribute('data-agent-extra-env-row', '');

        const keyInput = document.createElement('input');
        keyInput.type = 'text';
        keyInput.placeholder = 'Key，例如：HTTP_PROXY';
        keyInput.value = String(key || '');
        keyInput.setAttribute('data-agent-extra-env-key', '');

        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.placeholder = 'Value，例如：http://127.0.0.1:7890';
        valueInput.value = String(value || '');
        valueInput.setAttribute('data-agent-extra-env-value', '');

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'table-action-button table-action-button-danger settings-env-remove-button';
        removeButton.textContent = '删除';
        removeButton.setAttribute('data-agent-extra-env-remove', '');

        row.appendChild(keyInput);
        row.appendChild(valueInput);
        row.appendChild(removeButton);
        return row;
    }

    function syncAgentExtraEnvEmptyState() {
        if (!elements.agentExtraEnvList) {
            return;
        }

        const hasRows = Boolean(elements.agentExtraEnvList.querySelector('[data-agent-extra-env-row]'));
        const emptyNode = elements.agentExtraEnvList.querySelector('[data-agent-extra-env-empty]');
        if (hasRows) {
            if (emptyNode) {
                emptyNode.remove();
            }
            return;
        }

        if (emptyNode) {
            return;
        }

        const placeholder = document.createElement('div');
        placeholder.className = 'settings-env-empty';
        placeholder.setAttribute('data-agent-extra-env-empty', '');
        placeholder.textContent = '暂未设置额外环境变量';
        elements.agentExtraEnvList.appendChild(placeholder);
    }

    function addAgentExtraEnvRow(key, value, options) {
        if (!elements.agentExtraEnvList) {
            return null;
        }

        const emptyNode = elements.agentExtraEnvList.querySelector('[data-agent-extra-env-empty]');
        if (emptyNode) {
            emptyNode.remove();
        }

        const row = createAgentExtraEnvRow(key, value);
        elements.agentExtraEnvList.appendChild(row);
        if (options && options.focusKey) {
            const keyInput = row.querySelector('[data-agent-extra-env-key]');
            if (keyInput) {
                keyInput.focus();
            }
        }
        return row;
    }

    function renderAgentExtraEnvEditor(extraEnv) {
        if (!elements.agentExtraEnvList) {
            return;
        }

        elements.agentExtraEnvList.innerHTML = '';
        Object.entries(extraEnv || {}).forEach(function(entry) {
            addAgentExtraEnvRow(entry[0], entry[1]);
        });
        syncAgentExtraEnvEmptyState();
    }

    function clearAgentExtraEnvValidation() {
        if (!elements.agentExtraEnvList) {
            return;
        }

        elements.agentExtraEnvList.querySelectorAll('[data-agent-extra-env-key], [data-agent-extra-env-value]').forEach(function(node) {
            clearFieldInvalid(node);
        });
    }

    function collectAgentExtraEnvObject() {
        if (!elements.agentExtraEnvList) {
            return {};
        }

        const extraEnv = {};
        const seenKeys = new Set();
        let firstInvalidNode = null;

        elements.agentExtraEnvList.querySelectorAll('[data-agent-extra-env-row]').forEach(function(row) {
            const keyInput = row.querySelector('[data-agent-extra-env-key]');
            const valueInput = row.querySelector('[data-agent-extra-env-value]');
            const key = String(keyInput && keyInput.value || '').trim();
            const value = String(valueInput && valueInput.value || '');

            clearFieldInvalid(keyInput);
            clearFieldInvalid(valueInput);

            if (!key && !value) {
                return;
            }

            if (!key || seenKeys.has(key)) {
                markFieldInvalid(keyInput);
                if (!firstInvalidNode) {
                    firstInvalidNode = keyInput;
                }
                return;
            }

            seenKeys.add(key);
            extraEnv[key] = value;
        });

        if (firstInvalidNode) {
            firstInvalidNode.focus();
            throw new Error('额外环境变量的 Key 不能为空且不能重复。');
        }

        return extraEnv;
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
        return isDefault ? `${text}\u00a0\u00a0\u2B50` : text;
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
        const isDefaultHub = Boolean(selectedHubId) && selectedHubId === defaultHubId;
        const isDefaultAgent = Boolean(selectedAgentId) && selectedAgentId === defaultAgentId;
        const isDefaultModel = Boolean(selectedModelId) && selectedModelId === defaultModelId;
        setQuickActionButtonState(elements.hubSetDefaultQuickButton, {
            disabled: !selectedHubId || !selectedHub || isDefaultHub,
            text: isDefaultHub ? '已设默认' : '设为默认',
            title: !selectedHubId
                ? '请先选择平台'
                : isDefaultHub
                    ? '当前平台已是默认平台'
                    : '将当前平台设置为默认平台'
        });

        setQuickActionButtonState(elements.agentSetDefaultQuickButton, {
            disabled: !selectedAgentId || !selectedAgent || isDefaultAgent,
            text: isDefaultAgent ? '已设默认' : '设为默认',
            title: !selectedAgentId
                ? '请先选择 Agent'
                : isDefaultAgent
                    ? '当前 Agent 已是默认 Agent'
                    : '将当前 Agent 设置为默认 Agent'
        });

        setQuickActionButtonState(elements.modelSetDefaultQuickButton, {
            disabled: !selectedAgentId || !selectedModelId || isDefaultModel,
            text: isDefaultModel ? '已设默认' : '设为默认',
            title: !selectedAgentId
                ? '请先选择 Agent'
                : !selectedModelId
                    ? '请先选择模型'
                    : isDefaultModel
                        ? '当前模型已是默认模型'
                        : '将当前模型设置为默认模型'
        });

        setQuickActionButtonState(elements.modelRefreshQuickButton, {
            disabled: !selectedAgentId,
            text: '更新模型',
            title: selectedAgentId ? '更新当前 Agent 的模型列表' : '请先选择 Agent'
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
                formatDefaultOptionLabel(hub.id, hub.id === defaultHubId),
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
            setModelHint(agentMeta.model_error || '请到系统设置中拉取并保存该智能体的模型列表。');
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
                formatDefaultOptionLabel(agent.id, agent.id === defaultAgentId),
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
        if (state.editingAgentSettingsId && !agentIds.includes(state.editingAgentSettingsId)) {
            state.editingAgentSettingsId = '';
            state.isAgentSettingsModalOpen = false;
            state.isAgentFetchModelsModalOpen = false;
        }
        if (state.viewingAgentModelListId && !agentIds.includes(state.viewingAgentModelListId)) {
            state.isAgentModelListModalOpen = false;
            state.viewingAgentModelListId = '';
            state.viewingAgentModelIds = [];
            state.viewingAgentModelDefaultId = '';
        }
        if (!hubIds.includes(state.activeHubSettingsId)) {
            state.activeHubSettingsId = hubIds[0] || '';
        }
        if (state.editingHubSettingsId && !hubIds.includes(state.editingHubSettingsId)) {
            state.editingHubSettingsId = '';
            state.isHubSettingsModalOpen = false;
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
            appendOption(
                elements.agentDefaultModelSelect,
                modelId,
                modelId,
                {
                    selected: modelId === normalizedSelectedId
                }
            );
        });

        if (normalizedSelectedId && !normalizedIds.includes(normalizedSelectedId)) {
            appendOption(
                elements.agentDefaultModelSelect,
                normalizedSelectedId,
                `[已删除] ${normalizedSelectedId}`,
                {
                    selected: true
                }
            );
        }
    }

    function setAgentEditorDisabled(disabled) {
        [
            elements.agentSettingsId,
            elements.agentListModelsCommandInput,
            elements.agentReviewCommandInput,
            elements.agentDefaultModelSelect,
            elements.agentModelsTextarea,
            elements.agentAddEnvRowButton,
            elements.agentSaveButton
        ].forEach(function(node) {
            if (node) {
                node.disabled = disabled;
            }
        });
        if (elements.agentExtraEnvList) {
            elements.agentExtraEnvList.querySelectorAll('input, button').forEach(function(node) {
                node.disabled = disabled;
            });
        }
        syncAgentModelFetchButtonState(disabled);
    }

    function setHubEditorDisabled(disabled) {
        [
            elements.hubSettingsId,
            elements.hubTypeSelect,
            elements.hubWebBaseUrlInput,
            elements.hubApiBaseUrlInput,
            elements.hubPrivateTokenInput,
            elements.hubClonePreferenceSelect,
            elements.hubTimeoutInput,
            elements.hubVerifySslInput,
            elements.hubSaveButton
        ].forEach(function(node) {
            node.disabled = disabled;
        });
    }

    function getFormField(node) {
        return node ? node.closest('.form-field') : null;
    }

    function clearFieldInvalid(node) {
        if (!node) {
            return;
        }

        node.classList.remove('is-invalid');
        node.removeAttribute('aria-invalid');
        const field = getFormField(node);
        if (field) {
            field.classList.remove('is-invalid');
        }
    }

    function markFieldInvalid(node) {
        if (!node) {
            return;
        }

        node.classList.add('is-invalid');
        node.setAttribute('aria-invalid', 'true');
        const field = getFormField(node);
        if (field) {
            field.classList.add('is-invalid');
        }
    }

    function clearFieldInvalidList(nodes) {
        (nodes || []).forEach(function(node) {
            clearFieldInvalid(node);
        });
    }

    function clearAgentSettingsValidation() {
        clearFieldInvalidList([
            elements.agentSettingsId,
            elements.agentListModelsCommandInput,
            elements.agentReviewCommandInput
        ]);
        clearAgentExtraEnvValidation();
    }

    function getAgentModelPreviewRequestId() {
        const inputAgentId = String(elements.agentSettingsId.value || '').trim();
        const editingAgentId = String(state.editingAgentSettingsId || '').trim();
        return inputAgentId || editingAgentId || '__preview_agent__';
    }

    function syncAgentModelFetchButtonState(forceDisabled) {
        if (!elements.agentRefreshModelsButton) {
            return;
        }

        const hasListModelsCommand = Boolean(String(elements.agentListModelsCommandInput.value || '').trim());
        const isLoading = elements.agentRefreshModelsButton.classList.contains('is-loading');
        const shouldDisable = Boolean(forceDisabled) || !hasListModelsCommand;
        elements.agentRefreshModelsButton.disabled = isLoading || shouldDisable;
        elements.agentRefreshModelsButton.title = shouldDisable
            ? '请先填写拉模型命令'
            : '根据当前拉模型命令拉取模型列表';
    }

    function clearHubSettingsValidation() {
        clearFieldInvalidList([
            elements.hubSettingsId,
            elements.hubTypeSelect,
            elements.hubApiBaseUrlInput,
            elements.hubTimeoutInput
        ]);
    }

    function syncHubApiBaseUrlRequiredMark() {
        if (!elements.hubApiBaseUrlRequiredMark) {
            return;
        }

        const requiresApiBaseUrl = String(elements.hubTypeSelect.value || '').trim() === 'gitlab';
        elements.hubApiBaseUrlRequiredMark.hidden = !requiresApiBaseUrl;
    }

    function syncHubTimeoutValidity() {
        if (!elements.hubTimeoutInput) {
            return;
        }

        const input = elements.hubTimeoutInput;
        const rawValue = String(input.value || '').trim();
        input.setCustomValidity('');

        if (!rawValue) {
            return;
        }

        const numericValue = Number(rawValue);
        if (!Number.isFinite(numericValue) || !Number.isInteger(numericValue)) {
            input.setCustomValidity('请求超时秒数只能填写整数。');
            return;
        }

        if (numericValue < 1) {
            input.setCustomValidity('请求超时秒数必须大于等于 1。');
        }
    }

    function validateAgentSettingsForm() {
        clearAgentSettingsValidation();

        const nextAgentId = String(elements.agentSettingsId.value || '').trim();
        const listModelsCommand = String(elements.agentListModelsCommandInput.value || '').trim();
        const reviewCommand = String(elements.agentReviewCommandInput.value || '').trim();
        const invalidNodes = [];

        if (!nextAgentId) {
            invalidNodes.push(elements.agentSettingsId);
        }
        if (!listModelsCommand) {
            invalidNodes.push(elements.agentListModelsCommandInput);
        }
        if (!reviewCommand) {
            invalidNodes.push(elements.agentReviewCommandInput);
        }

        if (invalidNodes.length) {
            invalidNodes.forEach(function(node) {
                markFieldInvalid(node);
            });
            invalidNodes[0].focus();
            throw new Error('请填写标记为必填的 Agent 信息。');
        }

        return nextAgentId;
    }

    function validateHubSettingsForm() {
        clearHubSettingsValidation();

        const nextHubId = String(elements.hubSettingsId.value || '').trim();
        const hubType = String(elements.hubTypeSelect.value || '').trim();
        const apiBaseUrl = String(elements.hubApiBaseUrlInput.value || '').trim();
        const invalidNodes = [];
        syncHubTimeoutValidity();

        if (!nextHubId) {
            invalidNodes.push(elements.hubSettingsId);
        }
        if (!hubType) {
            invalidNodes.push(elements.hubTypeSelect);
        }
        if (hubType === 'gitlab' && !apiBaseUrl) {
            invalidNodes.push(elements.hubApiBaseUrlInput);
        }
        if (!elements.hubTimeoutInput.checkValidity()) {
            invalidNodes.push(elements.hubTimeoutInput);
        }

        if (invalidNodes.length) {
            invalidNodes.forEach(function(node) {
                markFieldInvalid(node);
            });
            invalidNodes[0].focus();
            throw new Error('请填写标记为必填的平台信息。');
        }

        return nextHubId;
    }

    function renderAgentSettingsList() {
        const agents = state.settings && Array.isArray(state.settings.agents) ? state.settings.agents : [];
        const paginatedAgents = paginateSettingsItems('agents', agents);
        renderSettingsTablePagination('agents', paginatedAgents.pagination);

        if (!agents.length) {
            elements.agentSettingsList.innerHTML = `
                <tr class="settings-empty-row">
                    <td colspan="6">暂无已配置智能体，点击“新增 Agent”开始创建。</td>
                </tr>
            `;
            return;
        }

        elements.agentSettingsList.innerHTML = paginatedAgents.items.map(function(agent) {
            const config = agent.config || {};
            const modelCount = collectAgentModelIds(agent).length;
            const defaultModel = String(config.default_model || '').trim() || '(未设置)';
            const listModelsCommand = String(config.list_models_command || '').trim() || '(未设置)';
            const reviewCommand = String(config.review_command || '').trim() || '(未设置)';
            const isActive = state.isAgentSettingsModalOpen && agent.id === state.activeAgentSettingsId;
            const deleteKey = getSettingsDeleteKey('agent', agent.id);
            const isDeletePending = getPendingSettingsDeleteKey() === deleteKey;
            const isDeleting = state.deletingSettingsDeleteKey === deleteKey;
            return `
                <tr class="${isActive ? 'is-active' : ''}">
                    <td>
                        <div class="settings-table-primary">
                            <div class="settings-table-name-row">
                                <span class="settings-table-name">${escapeHtml(agent.id)}</span>
                                ${agent.is_default ? '<span class="status-pill status-queued">默认</span>' : ''}
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="settings-table-secondary">${escapeHtml(defaultModel)}</span>
                    </td>
                    <td>
                        <button
                            type="button"
                            class="status-pill status-pill-button"
                            data-view-agent-models-id="${escapeHtml(agent.id)}"
                        >
                            ${escapeHtml(String(modelCount))} 个模型
                        </button>
                    </td>
                    <td>
                        <span class="settings-table-command">${escapeHtml(listModelsCommand)}</span>
                    </td>
                    <td>
                        <span class="settings-table-command">${escapeHtml(reviewCommand)}</span>
                    </td>
                    <td class="col-actions">
                        <div class="record-actions">
                            <button
                                type="button"
                                class="table-action-button table-action-button-edit"
                                data-agent-settings-id="${escapeHtml(agent.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                编辑
                            </button>
                            <button
                                type="button"
                                class="table-action-button table-action-button-danger${isDeletePending ? ' is-active' : ''}"
                                data-delete-agent-id="${escapeHtml(agent.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                删除
                            </button>
                            ${agent.is_default ? '' : `
                            <button
                                type="button"
                                class="field-link-button"
                                data-default-agent-id="${escapeHtml(agent.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                设为默认
                            </button>
                            `}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        syncSettingsDeletePopover();
    }

    function renderAgentSettingsEditor() {
        const editingAgentId = String(state.editingAgentSettingsId || '').trim();
        const agent = editingAgentId ? findSettingsAgent(editingAgentId) : null;
        const isCreateMode = !editingAgentId;

        if (!isCreateMode && !agent) {
            elements.agentSettingsTitle.textContent = 'Agent 不存在';
            elements.agentSettingsId.value = editingAgentId;
            elements.agentSettingsId.readOnly = true;
            elements.agentListModelsCommandInput.value = '';
            elements.agentReviewCommandInput.value = '';
            elements.agentModelsTextarea.value = '';
            renderAgentExtraEnvEditor({});
            renderAgentDefaultModelOptions([], '');
            elements.agentSaveButton.textContent = '保存';
            elements.agentRefreshModelsButton.textContent = '拉取模型';
            clearAgentSettingsValidation();
            setAgentEditorDisabled(true);
            return;
        }

        const config = agent ? (agent.config || {}) : {};
        const modelIds = agent ? collectAgentModelIds(agent) : [];
        const selectedDefaultModel = String((config.default_model || (agent && agent.default_model_id)) || '').trim();

        elements.agentSettingsTitle.textContent = isCreateMode ? '新增 Agent' : '编辑';
        elements.agentSettingsId.value = isCreateMode ? '' : agent.id;
        elements.agentSettingsId.readOnly = false;
        elements.agentListModelsCommandInput.value = config.list_models_command || '';
        elements.agentReviewCommandInput.value = config.review_command || '';
        elements.agentModelsTextarea.value = joinLineList(modelIds);
        renderAgentExtraEnvEditor(config.extra_env || {});
        renderAgentDefaultModelOptions(modelIds, selectedDefaultModel);
        clearAgentSettingsValidation();
        setAgentEditorDisabled(false);
        elements.agentRefreshModelsButton.textContent = '拉取模型';
        elements.agentSaveButton.textContent = isCreateMode ? '创建' : '保存';
    }

    function renderHubTypeOptions(selectedType) {
        const registeredTypes = state.settings && Array.isArray(state.settings.hub_types) ? state.settings.hub_types.slice() : [];
        const normalizedSelectedType = String(selectedType || '').trim();
        const resolvedSelectedType = normalizedSelectedType || registeredTypes[0] || '';
        if (resolvedSelectedType && !registeredTypes.includes(resolvedSelectedType)) {
            registeredTypes.push(resolvedSelectedType);
        }

        elements.hubTypeSelect.innerHTML = '';
        registeredTypes.forEach(function(hubType) {
            appendOption(elements.hubTypeSelect, hubType, hubType, {
                selected: hubType === resolvedSelectedType
            });
        });
    }

    function renderHubSettingsList() {
        const hubs = state.settings && Array.isArray(state.settings.hubs) ? state.settings.hubs : [];
        const paginatedHubs = paginateSettingsItems('hubs', hubs);
        renderSettingsTablePagination('hubs', paginatedHubs.pagination);

        if (!hubs.length) {
            elements.hubSettingsList.innerHTML = `
                <tr class="settings-empty-row">
                    <td colspan="5">暂无已配置平台，点击“新增平台”开始创建。</td>
                </tr>
            `;
            return;
        }

        elements.hubSettingsList.innerHTML = paginatedHubs.items.map(function(hub) {
            const config = hub.config || {};
            const isActive = state.isHubSettingsModalOpen && hub.id === state.activeHubSettingsId;
            const deleteKey = getSettingsDeleteKey('hub', hub.id);
            const isDeletePending = getPendingSettingsDeleteKey() === deleteKey;
            const isDeleting = state.deletingSettingsDeleteKey === deleteKey;
            return `
                <tr class="${isActive ? 'is-active' : ''}">
                    <td>
                        <div class="settings-table-primary">
                            <div class="settings-table-name-row">
                                <span class="settings-table-name">${escapeHtml(hub.id)}</span>
                                ${hub.is_default ? '<span class="status-pill status-queued">默认</span>' : ''}
                            </div>
                        </div>
                    </td>
                    <td>
                        <span class="settings-table-secondary">${escapeHtml(hub.type || config.type || '未知')}</span>
                    </td>
                    <td>
                        <span class="settings-table-code" title="${escapeHtml(config.web_base_url || '(未设置)')}">${escapeHtml(config.web_base_url || '(未设置)')}</span>
                    </td>
                    <td>
                        <span class="settings-table-code" title="${escapeHtml(config.api_base_url || '(未设置)')}">${escapeHtml(config.api_base_url || '(未设置)')}</span>
                    </td>
                    <td class="col-actions">
                        <div class="record-actions">
                            <button
                                type="button"
                                class="table-action-button table-action-button-edit"
                                data-hub-settings-id="${escapeHtml(hub.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                编辑
                            </button>
                            <button
                                type="button"
                                class="table-action-button table-action-button-danger${isDeletePending ? ' is-active' : ''}"
                                data-delete-hub-id="${escapeHtml(hub.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                删除
                            </button>
                            ${hub.is_default ? '' : `
                            <button
                                type="button"
                                class="field-link-button"
                                data-default-hub-id="${escapeHtml(hub.id)}"
                                ${isDeleting ? 'disabled' : ''}
                            >
                                设为默认
                            </button>
                            `}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        syncSettingsDeletePopover();
    }

    function renderHubSettingsEditor() {
        const editingHubId = String(state.editingHubSettingsId || '').trim();
        const hub = editingHubId ? findSettingsHub(editingHubId) : null;
        const isCreateMode = !editingHubId;

        if (!isCreateMode && !hub) {
            elements.hubSettingsTitle.textContent = '平台不存在';
            elements.hubSettingsId.value = editingHubId;
            elements.hubSettingsId.readOnly = true;
            renderHubTypeOptions('');
            elements.hubWebBaseUrlInput.value = '';
            elements.hubApiBaseUrlInput.value = '';
            elements.hubPrivateTokenInput.value = '';
            elements.hubClonePreferenceSelect.value = 'http';
            elements.hubTimeoutInput.value = '20';
            elements.hubVerifySslInput.checked = false;
            elements.hubSettingsHint.hidden = false;
            elements.hubSettingsHint.textContent = '当前平台不可用。';
            elements.hubSaveButton.textContent = '保存';
            clearHubSettingsValidation();
            syncHubApiBaseUrlRequiredMark();
            syncHubTimeoutValidity();
            setHubEditorDisabled(true);
            return;
        }

        const config = hub ? (hub.config || {}) : {};
        const hubType = hub ? (hub.type || config.type || '') : '';

        elements.hubSettingsTitle.textContent = isCreateMode ? '新增平台' : '编辑';
        elements.hubSettingsId.value = isCreateMode ? '' : hub.id;
        elements.hubSettingsId.readOnly = false;
        renderHubTypeOptions(hubType);
        elements.hubWebBaseUrlInput.value = config.web_base_url || '';
        elements.hubApiBaseUrlInput.value = config.api_base_url || '';
        elements.hubPrivateTokenInput.value = config.private_token || '';
        elements.hubClonePreferenceSelect.value = config.clone_url_preference || 'http';
        elements.hubTimeoutInput.value = String(config.timeout_seconds == null ? 20 : config.timeout_seconds);
        elements.hubVerifySslInput.checked = isCreateMode ? false : config.verify_ssl !== false;
        elements.hubSettingsHint.hidden = true;
        elements.hubSettingsHint.textContent = '';
        clearHubSettingsValidation();
        syncHubApiBaseUrlRequiredMark();
        syncHubTimeoutValidity();
        setHubEditorDisabled(false);
        elements.hubSaveButton.textContent = isCreateMode ? '创建' : '保存';
    }

    function renderSettings() {
        syncActiveSettingsIds();
        renderAgentSettingsList();
        renderHubSettingsList();
        renderAgentSettingsEditor();
        renderHubSettingsEditor();
        if (state.isAgentSettingsModalOpen) {
            openModal(elements.agentSettingsModal);
        } else {
            closeModal(elements.agentSettingsModal);
        }
        if (state.isHubSettingsModalOpen) {
            openModal(elements.hubSettingsModal);
        } else {
            closeModal(elements.hubSettingsModal);
        }
        if (state.isAgentFetchModelsModalOpen) {
            openModal(elements.agentFetchModelsModal);
        } else {
            closeModal(elements.agentFetchModelsModal);
        }
        if (state.isAgentModelListModalOpen) {
            openModal(elements.agentModelListModal);
        } else {
            closeModal(elements.agentModelListModal);
        }
        syncSettingsDeletePopover();
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
        const preferredEditingAgentSettingsId = hasOwn.call(payload, 'editingAgentSettingsId')
            ? payload.editingAgentSettingsId
            : state.editingAgentSettingsId;
        const preferredEditingHubSettingsId = hasOwn.call(payload, 'editingHubSettingsId')
            ? payload.editingHubSettingsId
            : state.editingHubSettingsId;
        const preferredAgentSettingsModalOpen = hasOwn.call(payload, 'agentSettingsModalOpen')
            ? payload.agentSettingsModalOpen
            : state.isAgentSettingsModalOpen;
        const preferredHubSettingsModalOpen = hasOwn.call(payload, 'hubSettingsModalOpen')
            ? payload.hubSettingsModalOpen
            : state.isHubSettingsModalOpen;

        state.isAgentFetchModelsModalOpen = false;
        closeModal(elements.agentFetchModelsModal);
        resetFetchedAgentModelPickerState();
        state.isAgentModelListModalOpen = false;
        closeModal(elements.agentModelListModal);
        resetAgentModelListViewerState();
        closeReviewCancelPopover(false);
        closeSettingsDeletePopover(false);

        const results = await Promise.all([
            requestJson('/api/meta'),
            requestJson('/api/settings')
        ]);

        state.meta = results[0];
        state.settings = results[1];
        state.activeAgentSettingsId = String(preferredAgentSettingsId || '');
        state.activeHubSettingsId = String(preferredHubSettingsId || '');
        state.editingAgentSettingsId = String(preferredEditingAgentSettingsId || '');
        state.editingHubSettingsId = String(preferredEditingHubSettingsId || '');
        state.isAgentSettingsModalOpen = Boolean(preferredAgentSettingsModalOpen);
        state.isHubSettingsModalOpen = Boolean(preferredHubSettingsModalOpen);

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
        if (record.status === 'cancelled') {
            return 'status-cancelled';
        }
        if (record.status === 'failed') {
            return 'status-failed';
        }
        if (record.runtime_state === 'canceling') {
            return 'status-canceling';
        }
        if (record.runtime_state === 'running') {
            return 'status-running';
        }
        return 'status-queued';
    }

    function renderStatusPill(record) {
        return `<span class="status-pill ${getStatusClass(record)}">${escapeHtml(record.status_label)}</span>`;
    }

    function isPendingReview(record) {
        return Boolean(record) && record.status === 'pending';
    }

    function isReviewCancelable(record) {
        return isPendingReview(record) && ['queued', 'running', 'canceling'].includes(String(record.runtime_state || ''));
    }

    function getCancelActionLabel(record) {
        if (!record) {
            return '取消';
        }
        if (record.runtime_state === 'running') {
            return '停止';
        }
        if (record.runtime_state === 'canceling') {
            return '停止中';
        }
        return '取消';
    }

    function renderReviewActionButtons(record) {
        const canCancel = isReviewCancelable(record);
        const cancelLabel = getCancelActionLabel(record);
        const cancelDisabled = record && record.runtime_state === 'canceling';
        const deleteDisabled = String(state.deletingReviewDeleteId || '') === String(record.id);

        return `
            <button type="button" class="table-action-button table-action-button-edit" data-view-review-id="${record.id}">详情</button>
            ${canCancel
                ? `<button type="button" class="table-action-button table-action-button-danger" data-cancel-review-id="${record.id}"${cancelDisabled ? ' disabled' : ''}>${escapeHtml(cancelLabel)}</button>`
                : `<button type="button" class="table-action-button table-action-button-danger" data-prefill-review-id="${record.id}">重试</button>`}
            <button type="button" class="table-action-button table-action-button-danger" data-delete-review-id="${record.id}"${deleteDisabled ? ' disabled' : ''}>删除</button>
        `;
    }

    function getSettingsTableState(tableKey) {
        return state.settingsTables[tableKey];
    }

    function getSettingsTableElements(tableKey) {
        if (tableKey === 'agents') {
            return {
                footer: elements.agentTableFooter,
                prevBtn: elements.agentPrevBtn,
                nextBtn: elements.agentNextBtn,
                pageInfo: elements.agentPageInfo,
                pageJumpInput: elements.agentPageJumpInput,
                pageSizeSelect: elements.agentPageSizeSelect,
                totalCount: elements.agentTotalCount
            };
        }

        return {
            footer: elements.hubTableFooter,
            prevBtn: elements.hubPrevBtn,
            nextBtn: elements.hubNextBtn,
            pageInfo: elements.hubPageInfo,
            pageJumpInput: elements.hubPageJumpInput,
            pageSizeSelect: elements.hubPageSizeSelect,
            totalCount: elements.hubTotalCount
        };
    }

    function getPinnedSettingsRowId(tableKey) {
        if (tableKey === 'agents') {
            return String(
                state.editingAgentSettingsId || (state.isAgentSettingsModalOpen ? state.activeAgentSettingsId : '') || ''
            ).trim();
        }

        return String(
            state.editingHubSettingsId || (state.isHubSettingsModalOpen ? state.activeHubSettingsId : '') || ''
        ).trim();
    }

    function buildLocalPagination(totalCount, page, pageSize) {
        const normalizedPageSize = Math.max(1, Number(pageSize) || 50);
        const normalizedTotalCount = Math.max(0, Number(totalCount) || 0);
        const totalPages = Math.max(1, Math.ceil(normalizedTotalCount / normalizedPageSize));
        const normalizedPage = Math.min(totalPages, Math.max(1, Number(page) || 1));

        return {
            page: normalizedPage,
            page_size: normalizedPageSize,
            total_pages: totalPages,
            total: normalizedTotalCount,
            has_prev: normalizedPage > 1,
            has_next: normalizedPage < totalPages
        };
    }

    function paginateSettingsItems(tableKey, items) {
        const tableState = getSettingsTableState(tableKey);
        const list = Array.isArray(items) ? items : [];
        let pagination = buildLocalPagination(list.length, tableState.page, tableState.pageSize);
        const pinnedId = getPinnedSettingsRowId(tableKey);

        if (pinnedId) {
            const pinnedIndex = list.findIndex(function(item) {
                return String((item && item.id) || '') === pinnedId;
            });

            if (pinnedIndex >= 0) {
                const startIndex = (pagination.page - 1) * pagination.page_size;
                const endIndex = startIndex + pagination.page_size;

                if (pinnedIndex < startIndex || pinnedIndex >= endIndex) {
                    tableState.page = Math.floor(pinnedIndex / pagination.page_size) + 1;
                    pagination = buildLocalPagination(list.length, tableState.page, tableState.pageSize);
                }
            }
        }

        tableState.page = pagination.page;
        tableState.pageSize = pagination.page_size;
        tableState.totalPages = pagination.total_pages;
        tableState.totalRecords = pagination.total;

        const sliceStart = (pagination.page - 1) * pagination.page_size;
        return {
            items: list.slice(sliceStart, sliceStart + pagination.page_size),
            pagination: pagination
        };
    }

    function renderSettingsTablePagination(tableKey, pagination) {
        const tableState = getSettingsTableState(tableKey);
        const tableElements = getSettingsTableElements(tableKey);
        const info = pagination || {};

        tableState.page = Number(info.page) || 1;
        tableState.pageSize = Number(info.page_size) || tableState.pageSize || 50;
        tableState.totalPages = Number(info.total_pages) || 1;
        tableState.totalRecords = Number(info.total) || 0;

        tableElements.pageInfo.textContent = `第 ${tableState.page} 页 / 共 ${tableState.totalPages} 页`;
        tableElements.totalCount.textContent = `共 ${tableState.totalRecords} 条`;
        tableElements.prevBtn.classList.toggle('disabled', !info.has_prev);
        tableElements.nextBtn.classList.toggle('disabled', !info.has_next);
        tableElements.pageJumpInput.max = String(tableState.totalPages);
        tableElements.pageJumpInput.value = String(tableState.page);
        tableElements.pageSizeSelect.value = String(tableState.pageSize);
        tableElements.footer.style.display = 'flex';
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
            elements.recordsTableBody.innerHTML = '<tr><td colspan="7" class="empty-row">暂无检视记录。</td></tr>';
            syncReviewCancelPopover();
            syncReviewDeletePopover();
            return;
        }

        elements.recordsTableBody.innerHTML = records.map(function(record) {
            const mrUrl = String(record.mr_url || '').trim();
            const mrTitle = record.title || mrUrl || '-';
            const escapedMrUrl = escapeHtml(mrUrl);
            const mrLinkMarkup = mrUrl
                ? `
                            <div class="record-link-row">
                                <a class="record-link" href="${escapedMrUrl}" target="_blank" rel="noreferrer">${escapedMrUrl}</a>
                                <button
                                    type="button"
                                    class="copy-link-button"
                                    data-copy-text="${escapedMrUrl}"
                                    data-copy-label="MR 地址"
                                    title="复制 MR 地址"
                                    aria-label="复制 MR 地址"
                                >
                                    ${COPY_LINK_ICON_MARKUP}
                                </button>
                            </div>
                        `
                : '<div class="record-subtitle">-</div>';
            return `
                <tr>
                    <td class="col-mr">
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(mrTitle)}</div>
                            ${mrLinkMarkup}
                        </div>
                    </td>
                    <td class="col-hub">${escapeHtml(record.hub_id)}</td>
                    <td class="col-agent">${escapeHtml(record.agent_id)}</td>
                    <td class="col-model">${escapeHtml(record.model_id)}</td>
                    <td class="col-status">${renderStatusPill(record)}</td>
                    <td class="col-time">
                        <div class="record-time">创建: ${escapeHtml(formatDate(record.created_at))}</div>
                        <div class="record-time">结束: ${record.finished_at ? escapeHtml(formatDate(record.finished_at)) : ''}</div>
                    </td>
                    <td class="col-actions">
                        <div class="record-actions">
                            ${renderReviewActionButtons(record)}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        syncReviewCancelPopover();
        syncReviewDeletePopover();
    }

    async function refreshReviews() {
        const params = new URLSearchParams({
            page: String(state.page),
            page_size: String(state.pageSize)
        });
        const payload = await requestJson(`/api/reviews?${params.toString()}`);
        renderRecords(payload.records || []);
        renderPagination(payload.pagination || {});
        syncReviewCancelPopover();
        syncReviewDeletePopover();

        if (state.openDetailId != null && !elements.detailModal.hidden) {
            await loadDetail(state.openDetailId, true);
            syncReviewCancelPopover();
            syncReviewDeletePopover();
        }
    }

    function syncModalBodyState() {
        const hasOpenModal = [
            elements.detailModal,
            elements.agentSettingsModal,
            elements.hubSettingsModal,
            elements.agentFetchModelsModal,
            elements.agentModelListModal
        ].some(function(modal) {
            return modal && !modal.hidden;
        });
        document.body.classList.toggle('modal-open', hasOpenModal);
    }

    function openModal(modal) {
        if (!modal) {
            return;
        }
        modal.hidden = false;
        syncModalBodyState();
    }

    function closeModal(modal) {
        if (!modal) {
            return;
        }
        modal.hidden = true;
        syncModalBodyState();
    }

    function openDetailModal() {
        openModal(elements.detailModal);
    }

    function closeDetailModal() {
        closeReviewCancelPopover();
        closeReviewDeletePopover();
        state.openDetailId = null;
        state.openDetailRecord = null;
        elements.detailContent.hidden = true;
        if (elements.detailCancelButton) {
            elements.detailCancelButton.hidden = true;
            elements.detailCancelButton.disabled = false;
            elements.detailCancelButton.textContent = '取消任务';
        }
        if (elements.detailDeleteButton) {
            elements.detailDeleteButton.hidden = true;
            elements.detailDeleteButton.disabled = false;
            elements.detailDeleteButton.textContent = '删除任务';
        }
        closeModal(elements.detailModal);
    }

    function openAgentSettingsModal(agentId) {
        const normalizedAgentId = String(agentId || '').trim();
        closeReviewCancelPopover();
        closeReviewDeletePopover();
        closeSettingsDeletePopover();
        closeAgentModelListViewer();
        state.isAgentSettingsModalOpen = true;
        state.editingAgentSettingsId = normalizedAgentId;
        if (normalizedAgentId) {
            state.activeAgentSettingsId = normalizedAgentId;
        }
        renderAgentSettingsList();
        renderAgentSettingsEditor();
        openModal(elements.agentSettingsModal);
    }

    function closeAgentSettingsModal() {
        closeAgentFetchModelsModal();
        state.isAgentSettingsModalOpen = false;
        state.editingAgentSettingsId = '';
        closeModal(elements.agentSettingsModal);
        renderAgentSettingsList();
    }

    function openHubSettingsModal(hubId) {
        const normalizedHubId = String(hubId || '').trim();
        closeReviewCancelPopover();
        closeReviewDeletePopover();
        closeSettingsDeletePopover();
        closeAgentModelListViewer();
        state.isHubSettingsModalOpen = true;
        state.editingHubSettingsId = normalizedHubId;
        if (normalizedHubId) {
            state.activeHubSettingsId = normalizedHubId;
        }
        renderHubSettingsList();
        renderHubSettingsEditor();
        openModal(elements.hubSettingsModal);
    }

    function closeHubSettingsModal() {
        state.isHubSettingsModalOpen = false;
        state.editingHubSettingsId = '';
        closeModal(elements.hubSettingsModal);
        renderHubSettingsList();
    }

    function renderDetail(detail) {
        const mrUrl = String(detail.mr_url || '').trim();
        const canCancel = isReviewCancelable(detail);
        const isDeleting = String(state.deletingReviewDeleteId || '') === String(detail.id);
        state.openDetailId = detail.id;
        state.openDetailRecord = detail;
        elements.detailStatusPill.className = `status-pill ${getStatusClass(detail)}`;
        elements.detailStatusPill.textContent = detail.status_label;
        elements.detailContent.hidden = false;
        if (elements.detailCancelButton) {
            elements.detailCancelButton.hidden = !canCancel;
            elements.detailCancelButton.disabled = detail.runtime_state === 'canceling';
            elements.detailCancelButton.textContent = getCancelActionLabel(detail);
        }
        if (elements.detailDeleteButton) {
            elements.detailDeleteButton.hidden = false;
            elements.detailDeleteButton.disabled = isDeleting;
            elements.detailDeleteButton.textContent = '删除任务';
        }

        elements.detailMrUrl.textContent = mrUrl || '-';
        if (mrUrl) {
            elements.detailMrUrl.href = mrUrl;
        } else {
            elements.detailMrUrl.removeAttribute('href');
        }
        resetCopyButtonState(elements.detailMrUrlCopyButton);
        if (elements.detailMrUrlCopyButton) {
            elements.detailMrUrlCopyButton.hidden = !mrUrl;
            elements.detailMrUrlCopyButton.disabled = !mrUrl;
            elements.detailMrUrlCopyButton.setAttribute('data-copy-text', mrUrl);
            resetCopyButtonState(elements.detailMrUrlCopyButton);
        }
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
        syncReviewCancelPopover();
        syncReviewDeletePopover();
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

    async function cancelReview(reviewId) {
        const payload = await requestJson(`/api/reviews/${reviewId}/cancel`, {
            method: 'POST'
        });

        if (payload.status === 'cancelled') {
            showToast('任务已取消。', 'success');
        } else {
            showToast('已发送停止请求，正在停止任务。', 'success');
        }

        await refreshReviews();
        return payload;
    }

    async function confirmReviewCancel() {
        const reviewId = getPendingReviewCancelKey();
        if (!reviewId) {
            return;
        }

        state.cancelingReviewCancelId = reviewId;
        syncReviewCancelPopover();

        try {
            await cancelReview(Number(reviewId));
            state.pendingReviewCancelId = '';
            state.pendingReviewCancelSource = '';
            state.cancelingReviewCancelId = '';
            hideReviewCancelPopover();
            syncReviewCancelTriggerState();
        } catch (error) {
            state.cancelingReviewCancelId = '';
            syncReviewCancelPopover();
            throw error;
        }
    }

    async function deleteReview(reviewId) {
        return requestJson(`/api/reviews/${reviewId}`, {
            method: 'DELETE'
        });
    }

    async function confirmReviewDelete() {
        const reviewId = getPendingReviewDeleteKey();
        if (!reviewId) {
            return;
        }

        state.deletingReviewDeleteId = reviewId;
        syncReviewDeletePopover();

        try {
            const payload = await deleteReview(Number(reviewId));
            state.pendingReviewDeleteId = '';
            state.pendingReviewDeleteSource = '';
            state.deletingReviewDeleteId = '';
            hideReviewDeletePopover();
            syncReviewDeleteTriggerState();

            if (state.openDetailRecord && String(state.openDetailRecord.id) === String(reviewId)) {
                closeDetailModal();
            }

            await refreshReviews();
            showToast(payload.stopped ? '任务已停止并删除。' : '任务已删除。', 'success');
        } catch (error) {
            state.deletingReviewDeleteId = '';
            syncReviewDeletePopover();
            throw error;
        }
    }

    function prefillReviewForm(record) {
        if (!record || !record.mr_url) {
            showToast('无法回填 MR 地址。', 'error');
            return;
        }

        closeReviewCancelPopover();
        closeReviewDeletePopover();
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

    function renderSettingsTable(tableKey) {
        if (tableKey === 'agents') {
            renderAgentSettingsList();
            return;
        }

        renderHubSettingsList();
    }

    function jumpToSettingsTablePage(tableKey, force) {
        const tableState = getSettingsTableState(tableKey);
        const tableElements = getSettingsTableElements(tableKey);
        const page = Number.parseInt(tableElements.pageJumpInput.value, 10);

        if (Number.isNaN(page)) {
            if (force) {
                tableElements.pageJumpInput.value = String(tableState.page);
            }
            return;
        }

        const targetPage = Math.min(tableState.totalPages, Math.max(1, page));
        if (targetPage === tableState.page) {
            tableElements.pageJumpInput.value = String(tableState.page);
            return;
        }

        tableState.page = targetPage;
        renderSettingsTable(tableKey);
    }

    function queueJumpToSettingsTablePage(tableKey) {
        const tableState = getSettingsTableState(tableKey);
        if (tableState.jumpDebounceTimer) {
            window.clearTimeout(tableState.jumpDebounceTimer);
        }

        tableState.jumpDebounceTimer = window.setTimeout(function() {
            jumpToSettingsTablePage(tableKey, false);
        }, 350);
    }

    function collectAgentSettingsPayload() {
        const models = parseLineList(elements.agentModelsTextarea.value);
        return {
            list_models_command: String(elements.agentListModelsCommandInput.value || '').trim(),
            review_command: String(elements.agentReviewCommandInput.value || '').trim(),
            models: models,
            default_model_id: models.includes(String(elements.agentDefaultModelSelect.value || '').trim())
                ? String(elements.agentDefaultModelSelect.value || '').trim()
                : '',
            extra_env: collectAgentExtraEnvObject()
        };
    }

    function collectAgentModelPreviewPayload() {
        return {
            agent_id: getAgentModelPreviewRequestId(),
            list_models_command: String(elements.agentListModelsCommandInput.value || '').trim(),
            review_command: String(elements.agentReviewCommandInput.value || '').trim(),
            extra_env: collectAgentExtraEnvObject()
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
        const nextAgentId = validateAgentSettingsForm();

        const requestAgentId = String(state.editingAgentSettingsId || nextAgentId).trim();
        const originalAgent = requestAgentId ? findSettingsAgent(requestAgentId) : null;
        const isCreateMode = !originalAgent;
        const isRename = Boolean(originalAgent) && requestAgentId !== nextAgentId;
        const payload = collectAgentSettingsPayload();
        payload.agent_id = nextAgentId;
        const currentReviewAgentId = String(elements.agentSelect.value || '');
        const currentReviewHubId = String(elements.hubSelect.value || '');
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(requestAgentId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const savedAgentId = String(response.id || nextAgentId || requestAgentId).trim();

        await reloadPageState({
            agentId: currentReviewAgentId === requestAgentId ? savedAgentId : currentReviewAgentId,
            hubId: currentReviewHubId,
            modelId: currentReviewAgentId === requestAgentId
                ? String(payload.default_model_id || currentReviewModelId)
                : currentReviewModelId,
            activeAgentSettingsId: savedAgentId,
            activeHubSettingsId: state.activeHubSettingsId,
            editingAgentSettingsId: '',
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: false,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        if (!options || !options.silent) {
            showToast(
                isRename
                    ? `Agent 已重命名为 ${savedAgentId}。`
                    : (isCreateMode ? 'Agent 已创建。' : '智能体配置已保存。'),
                'success'
            );
        }

        return response;
    }

    function ensureAgentModelFetchReady() {
        const agentId = getAgentModelPreviewRequestId();
        if (!agentId) {
            throw new Error('请先填写 Agent 名称。');
        }

        if (!String(elements.agentListModelsCommandInput.value || '').trim()) {
            throw new Error('请先填写拉模型命令，再拉取模型。');
        }

        return agentId;
    }

    async function fetchAgentModelPreviewFromSettings() {
        const agentId = ensureAgentModelFetchReady();
        const payload = collectAgentModelPreviewPayload();
        const response = await requestJson(`/api/agents/${encodeURIComponent(agentId)}/models/fetch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const fetchedModels = Array.isArray(response.fetched_models) ? response.fetched_models : [];
        const displayAgentId = String(elements.agentSettingsId.value || state.editingAgentSettingsId || '').trim();
        const fetchedCount = openAgentFetchModelPicker(fetchedModels, displayAgentId);
        showToast(
            fetchedCount
                ? `已获取到 ${fetchedCount} 个模型，请勾选后应用到当前清单。`
                : '没有拉取到可选模型。',
            'success'
        );
    }

    async function refreshAgentModelsFromSettings() {
        await fetchAgentModelPreviewFromSettings();
    }

    async function saveHubSettings() {
        const nextHubId = validateHubSettingsForm();

        const requestHubId = String(state.editingHubSettingsId || nextHubId).trim();
        const originalHub = requestHubId ? findSettingsHub(requestHubId) : null;
        const isCreateMode = !originalHub;
        const isRename = Boolean(originalHub) && requestHubId !== nextHubId;
        const payload = collectHubSettingsPayload();
        payload.hub_id = nextHubId;
        const currentReviewAgentId = String(elements.agentSelect.value || '');
        const currentReviewHubId = String(elements.hubSelect.value || '');
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(requestHubId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const savedHubId = String(response.id || nextHubId || requestHubId).trim();

        await reloadPageState({
            agentId: currentReviewAgentId,
            hubId: currentReviewHubId === requestHubId ? savedHubId : currentReviewHubId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: savedHubId,
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: '',
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: false
        });

        showToast(
            isRename
                ? `平台已重命名为 ${savedHubId}。`
                : (isCreateMode ? '平台已创建。' : '平台配置已保存。'),
            'success'
        );
        return response;
    }

    async function setDefaultAgentFromList(agentId) {
        const normalizedAgentId = String(agentId || '').trim();
        if (!normalizedAgentId) {
            throw new Error('缺少 Agent 名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(normalizedAgentId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: currentReviewHubId,
            agentId: currentReviewAgentId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: normalizedAgentId,
            activeHubSettingsId: state.activeHubSettingsId,
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        showToast(`已将 ${response.agent_id || normalizedAgentId} 设为默认 Agent。`, 'success');
    }

    async function setDefaultHubFromList(hubId) {
        const normalizedHubId = String(hubId || '').trim();
        if (!normalizedHubId) {
            throw new Error('缺少平台名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(normalizedHubId)}/default`, {
            method: 'POST'
        });

        await reloadPageState({
            hubId: currentReviewHubId,
            agentId: currentReviewAgentId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: normalizedHubId,
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        showToast(`已将 ${response.hub_id || normalizedHubId} 设为默认平台。`, 'success');
    }

    async function deleteAgentSettings(agentId) {
        const normalizedAgentId = String(agentId || state.editingAgentSettingsId || '').trim();
        if (!normalizedAgentId) {
            throw new Error('缺少 Agent 名称。');
        }
        if (!window.confirm(`删除 Agent“${normalizedAgentId}”？`)) {
            return false;
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(normalizedAgentId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId,
            agentId: currentReviewAgentId === normalizedAgentId ? String(response.agent_id || '') : currentReviewAgentId,
            modelId: currentReviewAgentId === normalizedAgentId ? '' : currentReviewModelId,
            activeAgentSettingsId: '',
            activeHubSettingsId: state.activeHubSettingsId,
            editingAgentSettingsId: '',
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: false,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        showToast('Agent 已删除。', 'success');
        return true;
    }

    async function deleteHubSettings(hubId) {
        const normalizedHubId = String(hubId || state.editingHubSettingsId || '').trim();
        if (!normalizedHubId) {
            throw new Error('缺少平台名称。');
        }
        if (!window.confirm(`删除平台“${normalizedHubId}”？`)) {
            return false;
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(normalizedHubId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId === normalizedHubId ? String(response.hub_id || '') : currentReviewHubId,
            agentId: currentReviewAgentId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: '',
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: '',
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: false
        });

        showToast('平台已删除。', 'success');
        return true;
    }

    async function refreshAgentModelsFromSettings() {
        await fetchAgentModelPreviewFromSettings();
    }

    async function deleteAgentSettings(agentId) {
        const normalizedAgentId = String(agentId || state.editingAgentSettingsId || '').trim();
        if (!normalizedAgentId) {
            throw new Error('缺少 Agent 名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(normalizedAgentId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId,
            agentId: currentReviewAgentId === normalizedAgentId ? String(response.agent_id || '') : currentReviewAgentId,
            modelId: currentReviewAgentId === normalizedAgentId ? '' : currentReviewModelId,
            activeAgentSettingsId: '',
            activeHubSettingsId: state.activeHubSettingsId,
            editingAgentSettingsId: '',
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: false,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        showToast('Agent 已删除。', 'success');
        return true;
    }

    async function deleteHubSettings(hubId) {
        const normalizedHubId = String(hubId || state.editingHubSettingsId || '').trim();
        if (!normalizedHubId) {
            throw new Error('缺少平台名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(normalizedHubId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId === normalizedHubId ? String(response.hub_id || '') : currentReviewHubId,
            agentId: currentReviewAgentId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: '',
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: '',
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: false
        });

        showToast('平台已删除。', 'success');
        return true;
    }

    async function confirmSettingsDelete() {
        const kind = state.pendingSettingsDeleteKind;
        const id = String(state.pendingSettingsDeleteId || '').trim();
        const deleteKey = getPendingSettingsDeleteKey();
        if (!deleteKey) {
            return;
        }

        state.deletingSettingsDeleteKey = deleteKey;
        syncSettingsDeletePopover();

        try {
            if (kind === 'hub') {
                await deleteHubSettings(id);
            } else {
                await deleteAgentSettings(id);
            }
            state.pendingSettingsDeleteKind = '';
            state.pendingSettingsDeleteId = '';
            state.deletingSettingsDeleteKey = '';
            hideSettingsDeletePopover();
            syncSettingsDeleteTriggerState();
        } catch (error) {
            state.deletingSettingsDeleteKey = '';
            syncSettingsDeletePopover();
            throw error;
        }
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
        showToast(`已更新 ${modelCount} 个模型。`, 'success');
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

        if (!payload.hub_id) {
            showToast('请选择平台。', 'error');
            elements.hubSelect.focus();
            return;
        }

        if (!payload.agent_id) {
            showToast('请选择 Agent。', 'error');
            elements.agentSelect.focus();
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
            elements.mrUrlInput.value = '';
            elements.mrUrlInput.focus();
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

        document.addEventListener('click', function(event) {
            if (event.target.closest('#settingsDeletePopover')) {
                return;
            }
            if (event.target.closest('#reviewCancelPopover')) {
                return;
            }
            if (event.target.closest('#reviewDeletePopover')) {
                return;
            }
            if (event.target.closest('[data-delete-agent-id], [data-delete-hub-id]')) {
                return;
            }
            if (event.target.closest('[data-cancel-review-id], #detailCancelButton')) {
                return;
            }
            if (event.target.closest('[data-delete-review-id], #detailDeleteButton')) {
                return;
            }
            closeReviewCancelPopover();
            closeReviewDeletePopover();
            closeSettingsDeletePopover();
        });

        window.addEventListener('resize', function() {
            closeReviewCancelPopover(false);
            closeReviewDeletePopover(false);
            closeSettingsDeletePopover(false);
        });

        window.addEventListener('scroll', function() {
            closeReviewCancelPopover(false);
            closeReviewDeletePopover(false);
            closeSettingsDeletePopover(false);
        }, true);

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
            }, {
                preserveLabel: true,
                lockWidth: false
            }).then(function() {
                syncReviewFormQuickActions();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            }).finally(function() {
                syncAgentModelFetchButtonState();
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

        ['agents', 'hubs'].forEach(function(tableKey) {
            const tableState = getSettingsTableState(tableKey);
            const tableElements = getSettingsTableElements(tableKey);

            tableElements.prevBtn.addEventListener('click', function() {
                if (tableState.page <= 1) {
                    return;
                }

                tableState.page -= 1;
                renderSettingsTable(tableKey);
            });

            tableElements.nextBtn.addEventListener('click', function() {
                if (tableState.page >= tableState.totalPages) {
                    return;
                }

                tableState.page += 1;
                renderSettingsTable(tableKey);
            });

            [tableElements.prevBtn, tableElements.nextBtn].forEach(function(node) {
                node.addEventListener('keydown', function(event) {
                    if (event.key !== 'Enter' && event.key !== ' ') {
                        return;
                    }
                    event.preventDefault();
                    node.click();
                });
            });

            tableElements.pageJumpInput.addEventListener('input', function() {
                queueJumpToSettingsTablePage(tableKey);
            });
            tableElements.pageJumpInput.addEventListener('blur', function() {
                jumpToSettingsTablePage(tableKey, true);
            });
            tableElements.pageJumpInput.addEventListener('keydown', function(event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    jumpToSettingsTablePage(tableKey, true);
                }
            });

            tableElements.pageSizeSelect.addEventListener('change', function() {
                const nextPageSize = Number.parseInt(tableElements.pageSizeSelect.value, 10);
                if (!Number.isFinite(nextPageSize) || nextPageSize <= 0 || nextPageSize === tableState.pageSize) {
                    return;
                }

                tableState.pageSize = nextPageSize;
                tableState.page = 1;
                renderSettingsTable(tableKey);
            });
        });

        elements.recordsTableBody.addEventListener('click', function(event) {
            const copyButton = event.target.closest('[data-copy-text]');
            if (copyButton) {
                event.preventDefault();
                event.stopPropagation();
                copyFromButton(copyButton);
                return;
            }

            const viewButton = event.target.closest('[data-view-review-id]');
            if (viewButton) {
                const reviewId = Number(viewButton.getAttribute('data-view-review-id'));
                loadDetail(reviewId).catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
                return;
            }

            const cancelButton = event.target.closest('[data-cancel-review-id]');
            if (cancelButton) {
                const reviewId = Number(cancelButton.getAttribute('data-cancel-review-id'));
                openReviewCancelPopover(reviewId, 'table');
                return;
            }

            const deleteButton = event.target.closest('[data-delete-review-id]');
            if (deleteButton) {
                const reviewId = Number(deleteButton.getAttribute('data-delete-review-id'));
                openReviewDeletePopover(reviewId, 'table');
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

        if (elements.detailCancelButton) {
            elements.detailCancelButton.addEventListener('click', function() {
                if (!state.openDetailRecord) {
                    return;
                }
                openReviewCancelPopover(state.openDetailRecord.id, 'detail');
            });
        }

        if (elements.detailDeleteButton) {
            elements.detailDeleteButton.addEventListener('click', function() {
                if (!state.openDetailRecord) {
                    return;
                }
                openReviewDeletePopover(state.openDetailRecord.id, 'detail');
            });
        }

        if (elements.detailMrUrlCopyButton) {
            elements.detailMrUrlCopyButton.addEventListener('click', function(event) {
                event.preventDefault();
                copyFromButton(elements.detailMrUrlCopyButton);
            });
        }

        document.querySelectorAll('[data-close-detail-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeDetailModal();
            });
        });

        document.querySelectorAll('[data-close-agent-settings-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeAgentSettingsModal();
            });
        });

        document.querySelectorAll('[data-close-hub-settings-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeHubSettingsModal();
            });
        });

        document.querySelectorAll('[data-close-agent-fetch-models-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeAgentFetchModelsModal();
            });
        });

        document.querySelectorAll('[data-close-agent-model-list-modal]').forEach(function(node) {
            node.addEventListener('click', function() {
                closeAgentModelListViewer();
            });
        });

        if (elements.settingsDeleteCancelButton) {
            elements.settingsDeleteCancelButton.addEventListener('click', function(event) {
                event.preventDefault();
                closeSettingsDeletePopover();
            });
        }

        if (elements.settingsDeleteConfirmButton) {
            elements.settingsDeleteConfirmButton.addEventListener('click', function(event) {
                event.preventDefault();
                confirmSettingsDelete().catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
            });
        }

        if (elements.reviewCancelCancelButton) {
            elements.reviewCancelCancelButton.addEventListener('click', function(event) {
                event.preventDefault();
                closeReviewCancelPopover();
            });
        }

        if (elements.reviewCancelConfirmButton) {
            elements.reviewCancelConfirmButton.addEventListener('click', function(event) {
                event.preventDefault();
                confirmReviewCancel().catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
            });
        }

        if (elements.reviewDeleteCancelButton) {
            elements.reviewDeleteCancelButton.addEventListener('click', function(event) {
                event.preventDefault();
                closeReviewDeletePopover();
            });
        }

        if (elements.reviewDeleteConfirmButton) {
            elements.reviewDeleteConfirmButton.addEventListener('click', function(event) {
                event.preventDefault();
                confirmReviewDelete().catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
            });
        }

        document.addEventListener('keydown', function(event) {
            if (event.key !== 'Escape') {
                return;
            }
            if (getPendingReviewCancelKey()) {
                closeReviewCancelPopover();
                return;
            }
            if (getPendingReviewDeleteKey()) {
                closeReviewDeletePopover();
                return;
            }
            if (state.isAgentModelListModalOpen) {
                closeAgentModelListViewer();
                return;
            }
            if (state.isAgentFetchModelsModalOpen) {
                closeAgentFetchModelsModal();
                return;
            }
            if (state.isAgentSettingsModalOpen) {
                closeAgentSettingsModal();
                return;
            }
            if (state.isHubSettingsModalOpen) {
                closeHubSettingsModal();
                return;
            }
            if (!elements.detailModal.hidden) {
                closeDetailModal();
            }
        });

        elements.agentSettingsList.addEventListener('click', function(event) {
            const viewButton = event.target.closest('[data-view-agent-models-id]');
            if (!viewButton) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            openAgentModelListViewer(viewButton.getAttribute('data-view-agent-models-id') || '');
        }, true);

        elements.agentSettingsList.addEventListener('click', function(event) {
            const deleteButton = event.target.closest('[data-delete-agent-id]');
            if (!deleteButton) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            openSettingsDeletePopover('agent', deleteButton.getAttribute('data-delete-agent-id') || '');
        }, true);

        elements.hubSettingsList.addEventListener('click', function(event) {
            const deleteButton = event.target.closest('[data-delete-hub-id]');
            if (!deleteButton) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
            openSettingsDeletePopover('hub', deleteButton.getAttribute('data-delete-hub-id') || '');
        }, true);

        elements.agentCreateButton.addEventListener('click', function() {
            openAgentSettingsModal('');
        });

        elements.agentSettingsList.addEventListener('click', function(event) {
            const editButton = event.target.closest('[data-agent-settings-id]');
            if (editButton) {
                openAgentSettingsModal(editButton.getAttribute('data-agent-settings-id') || '');
                return;
            }

            const deleteButton = event.target.closest('[data-delete-agent-id]');
            if (deleteButton) {
                runWithBusyButton(deleteButton, '删除中...', function() {
                    return deleteAgentSettings(deleteButton.getAttribute('data-delete-agent-id') || '');
                }).catch(function(error) {
                    if (error) {
                        showToast(error.message || String(error), 'error');
                    }
                });
                return;
            }

            const defaultButton = event.target.closest('[data-default-agent-id]');
            if (defaultButton) {
                runWithBusyButton(defaultButton, '更新中...', function() {
                    return setDefaultAgentFromList(defaultButton.getAttribute('data-default-agent-id') || '');
                }).catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
            }
        });

        elements.hubCreateButton.addEventListener('click', function() {
            openHubSettingsModal('');
        });

        elements.hubSettingsList.addEventListener('click', function(event) {
            const editButton = event.target.closest('[data-hub-settings-id]');
            if (editButton) {
                openHubSettingsModal(editButton.getAttribute('data-hub-settings-id') || '');
                return;
            }

            const deleteButton = event.target.closest('[data-delete-hub-id]');
            if (deleteButton) {
                runWithBusyButton(deleteButton, '删除中...', function() {
                    return deleteHubSettings(deleteButton.getAttribute('data-delete-hub-id') || '');
                }).catch(function(error) {
                    if (error) {
                        showToast(error.message || String(error), 'error');
                    }
                });
                return;
            }

            const defaultButton = event.target.closest('[data-default-hub-id]');
            if (defaultButton) {
                runWithBusyButton(defaultButton, '更新中...', function() {
                    return setDefaultHubFromList(defaultButton.getAttribute('data-default-hub-id') || '');
                }).catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
            }
        });

        elements.agentModelsTextarea.addEventListener('input', function() {
            syncAgentDefaultModelOptionsFromForm();
        });

        [
            elements.agentSettingsId,
            elements.agentListModelsCommandInput,
            elements.agentReviewCommandInput
        ].forEach(function(node) {
            node.addEventListener('input', function() {
                clearFieldInvalid(node);
                if (node === elements.agentListModelsCommandInput) {
                    syncAgentModelFetchButtonState();
                }
            });
        });

        if (elements.agentAddEnvRowButton) {
            elements.agentAddEnvRowButton.addEventListener('click', function() {
                addAgentExtraEnvRow('', '', { focusKey: true });
            });
        }

        if (elements.agentExtraEnvList) {
            elements.agentExtraEnvList.addEventListener('input', function(event) {
                const input = event.target.closest('[data-agent-extra-env-key], [data-agent-extra-env-value]');
                if (!input) {
                    return;
                }
                clearFieldInvalid(input);
            });

            elements.agentExtraEnvList.addEventListener('click', function(event) {
                const removeButton = event.target.closest('[data-agent-extra-env-remove]');
                if (!removeButton) {
                    return;
                }

                const row = removeButton.closest('[data-agent-extra-env-row]');
                if (row) {
                    row.remove();
                    syncAgentExtraEnvEmptyState();
                }
            });
        }

        elements.hubSettingsId.addEventListener('input', function() {
            clearFieldInvalid(elements.hubSettingsId);
        });

        elements.hubTypeSelect.addEventListener('change', function() {
            clearFieldInvalid(elements.hubTypeSelect);
            clearFieldInvalid(elements.hubApiBaseUrlInput);
            syncHubApiBaseUrlRequiredMark();
        });

        elements.hubApiBaseUrlInput.addEventListener('input', function() {
            clearFieldInvalid(elements.hubApiBaseUrlInput);
        });

        elements.hubTimeoutInput.addEventListener('input', function() {
            clearFieldInvalid(elements.hubTimeoutInput);
            syncHubTimeoutValidity();
        });

        elements.hubTimeoutInput.addEventListener('invalid', function() {
            syncHubTimeoutValidity();
            markFieldInvalid(elements.hubTimeoutInput);
        });

        elements.agentSettingsForm.addEventListener('submit', function(event) {
            event.preventDefault();
            runWithBusyButton(elements.agentSaveButton, '保存中...', function() {
                return saveAgentSettings();
            }, {
                preserveLabel: true,
                lockWidth: false
            }).then(function() {
                renderAgentSettingsEditor();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.agentRefreshModelsButton.addEventListener('click', function() {
            runWithBusyButton(elements.agentRefreshModelsButton, '拉取中...', function() {
                return refreshAgentModelsFromSettings();
            }, {
                preserveLabel: true,
                lockWidth: false
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.hubSettingsForm.addEventListener('submit', function(event) {
            event.preventDefault();
            runWithBusyButton(elements.hubSaveButton, '保存中...', function() {
                return saveHubSettings();
            }, {
                preserveLabel: true,
                lockWidth: false
            }).then(function() {
                renderHubSettingsEditor();
            }).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });
    }

    function syncSettingsDeletePopover() {
        syncSettingsDeleteTriggerState();

        if (!elements.settingsDeletePopover || !elements.settingsDeleteConfirmButton || !elements.settingsDeleteConfirmText) {
            return;
        }

        const kind = state.pendingSettingsDeleteKind;
        const id = String(state.pendingSettingsDeleteId || '').trim();
        const pendingKey = getPendingSettingsDeleteKey();
        if (!pendingKey) {
            hideSettingsDeletePopover();
            return;
        }

        const trigger = getSettingsDeleteTrigger(kind, id);
        if (!trigger) {
            state.pendingSettingsDeleteKind = '';
            state.pendingSettingsDeleteId = '';
            state.deletingSettingsDeleteKey = '';
            syncSettingsDeleteTriggerState();
            hideSettingsDeletePopover();
            return;
        }

        const label = kind === 'hub' ? '平台' : 'Agent';
        const isDeleting = state.deletingSettingsDeleteKey === pendingKey;
        elements.settingsDeleteConfirmText.textContent = `删除${label}“${id}”？`;
        elements.settingsDeleteConfirmButton.disabled = isDeleting;
        elements.settingsDeleteConfirmButton.textContent = isDeleting ? '删除中...' : '确认';

        elements.settingsDeletePopover.hidden = false;

        const triggerRect = trigger.getBoundingClientRect();
        const popoverRect = elements.settingsDeletePopover.getBoundingClientRect();
        const viewportPadding = 12;
        const offset = 10;
        const canPlaceBottom = triggerRect.bottom + offset + popoverRect.height <= window.innerHeight - viewportPadding;
        const shouldPlaceBottom = canPlaceBottom || triggerRect.top < popoverRect.height + viewportPadding + offset;
        const top = shouldPlaceBottom
            ? Math.min(window.innerHeight - popoverRect.height - viewportPadding, triggerRect.bottom + offset)
            : Math.max(viewportPadding, triggerRect.top - popoverRect.height - offset);
        const left = Math.min(
            window.innerWidth - popoverRect.width - viewportPadding,
            Math.max(viewportPadding, triggerRect.left + ((triggerRect.width - popoverRect.width) / 2))
        );
        const arrowLeft = Math.min(
            popoverRect.width - 18,
            Math.max(18, triggerRect.left + (triggerRect.width / 2) - left)
        );

        elements.settingsDeletePopover.dataset.placement = shouldPlaceBottom ? 'bottom' : 'top';
        elements.settingsDeletePopover.style.top = `${top}px`;
        elements.settingsDeletePopover.style.left = `${left}px`;
        elements.settingsDeletePopover.style.setProperty('--popover-arrow-left', `${arrowLeft}px`);
    }

    async function refreshAgentModelsFromSettings() {
        await fetchAgentModelPreviewFromSettings();
    }

    async function deleteAgentSettings(agentId) {
        const normalizedAgentId = String(agentId || state.editingAgentSettingsId || '').trim();
        if (!normalizedAgentId) {
            throw new Error('缺少 Agent 名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/agents/${encodeURIComponent(normalizedAgentId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId,
            agentId: currentReviewAgentId === normalizedAgentId ? String(response.agent_id || '') : currentReviewAgentId,
            modelId: currentReviewAgentId === normalizedAgentId ? '' : currentReviewModelId,
            activeAgentSettingsId: '',
            activeHubSettingsId: state.activeHubSettingsId,
            editingAgentSettingsId: '',
            editingHubSettingsId: state.editingHubSettingsId,
            agentSettingsModalOpen: false,
            hubSettingsModalOpen: state.isHubSettingsModalOpen
        });

        showToast('Agent 已删除。', 'success');
        return true;
    }

    async function deleteHubSettings(hubId) {
        const normalizedHubId = String(hubId || state.editingHubSettingsId || '').trim();
        if (!normalizedHubId) {
            throw new Error('缺少平台名称。');
        }

        const currentReviewHubId = String(elements.hubSelect.value || '').trim();
        const currentReviewAgentId = String(elements.agentSelect.value || '').trim();
        const currentReviewModelId = String(elements.modelSelect.value || '').trim();
        const response = await requestJson(`/api/settings/hubs/${encodeURIComponent(normalizedHubId)}`, {
            method: 'DELETE'
        });

        await reloadPageState({
            hubId: currentReviewHubId === normalizedHubId ? String(response.hub_id || '') : currentReviewHubId,
            agentId: currentReviewAgentId,
            modelId: currentReviewModelId,
            activeAgentSettingsId: state.activeAgentSettingsId,
            activeHubSettingsId: '',
            editingAgentSettingsId: state.editingAgentSettingsId,
            editingHubSettingsId: '',
            agentSettingsModalOpen: state.isAgentSettingsModalOpen,
            hubSettingsModalOpen: false
        });

        showToast('平台已删除。', 'success');
        return true;
    }

    async function confirmSettingsDelete() {
        const kind = state.pendingSettingsDeleteKind;
        const id = String(state.pendingSettingsDeleteId || '').trim();
        const deleteKey = getPendingSettingsDeleteKey();
        if (!deleteKey) {
            return;
        }

        state.deletingSettingsDeleteKey = deleteKey;
        syncSettingsDeletePopover();

        try {
            if (kind === 'hub') {
                await deleteHubSettings(id);
            } else {
                await deleteAgentSettings(id);
            }
            state.pendingSettingsDeleteKind = '';
            state.pendingSettingsDeleteId = '';
            state.deletingSettingsDeleteKey = '';
            hideSettingsDeletePopover();
            syncSettingsDeleteTriggerState();
        } catch (error) {
            state.deletingSettingsDeleteKey = '';
            syncSettingsDeletePopover();
            throw error;
        }
    }

    function bindSupplementalEvents() {
        if (elements.agentModelListSearchInput) {
            elements.agentModelListSearchInput.addEventListener('input', function() {
                renderAgentModelListViewer();
            });
        }

        if (elements.agentFetchModelSearchInput) {
            elements.agentFetchModelSearchInput.addEventListener('input', function() {
                renderFetchedAgentModelPicker();
            });
        }

        if (elements.agentFetchModelSelectAllCheckbox) {
            elements.agentFetchModelSelectAllCheckbox.addEventListener('change', function() {
                toggleFilteredFetchedAgentModels(Boolean(elements.agentFetchModelSelectAllCheckbox.checked));
            });
        }

        if (elements.agentFetchModelListBody) {
            elements.agentFetchModelListBody.addEventListener('change', function(event) {
                const checkbox = event.target.closest('[data-fetched-agent-model]');
                if (!checkbox) {
                    return;
                }

                toggleFetchedAgentModelSelection(
                    decodeURIComponent(checkbox.getAttribute('data-fetched-agent-model') || ''),
                    Boolean(checkbox.checked),
                    checkbox
                );
            });
        }

        if (elements.agentApplyFetchedModelsButton) {
            elements.agentApplyFetchedModelsButton.addEventListener('click', function() {
                applyFetchedAgentModelSelection();
            });
        }
    }

    async function bootstrap() {
        if (window.initThemeToggle) {
            window.initThemeToggle();
        }

        bindEvents();
        bindSupplementalEvents();
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
