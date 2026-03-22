(function() {
    const state = {
        meta: null,
        records: [],
        openDetailId: null,
        openDetailRecord: null,
        refreshTimer: null,
        autoRefreshEnabled: false,
        page: 1,
        pageSize: 50,
        totalPages: 1,
        totalRecords: 0,
        jumpDebounceTimer: null
    };

    const elements = {};

    function cacheElements() {
        elements.reviewForm = document.getElementById('reviewForm');
        elements.mrUrlInput = document.getElementById('mrUrlInput');
        elements.hubSelect = document.getElementById('hubSelect');
        elements.agentSelect = document.getElementById('agentSelect');
        elements.modelSelect = document.getElementById('modelSelect');
        elements.refreshModelsButton = document.getElementById('refreshModelsButton');
        elements.modelHint = document.getElementById('modelHint');
        elements.queueRefreshButton = document.getElementById('queueRefreshButton');
        elements.autoRefreshToggleButton = document.getElementById('autoRefreshToggleButton');
        elements.tableFooter = document.getElementById('tableFooter');
        elements.prevBtn = document.getElementById('prevBtn');
        elements.nextBtn = document.getElementById('nextBtn');
        elements.pageInfo = document.getElementById('pageInfo');
        elements.pageJumpInput = document.getElementById('pageJumpInput');
        elements.pageSizeSelect = document.getElementById('pageSizeSelect');
        elements.totalCount = document.getElementById('totalCount');
        elements.submitButton = document.getElementById('submitButton');
        elements.recordsTableBody = document.getElementById('recordsTableBody');
        elements.toastStack = document.getElementById('toastStack');

        elements.detailModal = document.getElementById('detailModal');
        elements.detailCloseButton = document.getElementById('detailCloseButton');
        elements.detailStatusPill = document.getElementById('detailStatusPill');
        elements.detailPrefillButton = document.getElementById('detailPrefillButton');
        elements.detailContent = document.getElementById('detailContent');
        elements.detailId = document.getElementById('detailId');
        elements.detailQueuePosition = document.getElementById('detailQueuePosition');
        elements.detailMrUrl = document.getElementById('detailMrUrl');
        elements.detailHub = document.getElementById('detailHub');
        elements.detailAgent = document.getElementById('detailAgent');
        elements.detailModel = document.getElementById('detailModel');
        elements.detailSourceBranch = document.getElementById('detailSourceBranch');
        elements.detailTargetBranch = document.getElementById('detailTargetBranch');
        elements.detailCreatedAt = document.getElementById('detailCreatedAt');
        elements.detailStartedAt = document.getElementById('detailStartedAt');
        elements.detailFinishedAt = document.getElementById('detailFinishedAt');
        elements.detailWorkingDirectory = document.getElementById('detailWorkingDirectory');
        elements.detailCommand = document.getElementById('detailCommand');
        elements.detailResult = document.getElementById('detailResult');
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

        return date.toLocaleString('zh-CN', {
            hour12: false
        });
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function showToast(message, variant) {
        const item = document.createElement('div');
        item.className = `toast ${variant ? `toast-${variant}` : ''}`.trim();
        item.textContent = message;
        elements.toastStack.appendChild(item);
        window.setTimeout(function() {
            item.remove();
        }, 3600);
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

    function findAgentMeta(agentId) {
        if (!state.meta) {
            return null;
        }
        return state.meta.agents.find(function(agent) {
            return agent.id === agentId;
        }) || null;
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

    function setModelHint(message) {
        const text = String(message || '').trim();
        elements.modelHint.textContent = text;
        elements.modelHint.hidden = !text;
    }

    function populateHubSelect() {
        const defaults = state.meta.defaults || {};
        elements.hubSelect.innerHTML = '';

        state.meta.hubs.forEach(function(hub) {
            const option = document.createElement('option');
            option.value = hub.id;
            option.textContent = hub.name;
            if (hub.id === defaults.hub_id) {
                option.selected = true;
            }
            elements.hubSelect.appendChild(option);
        });

        if (!elements.hubSelect.value && state.meta.hubs.length > 0) {
            elements.hubSelect.value = state.meta.hubs[0].id;
        }
    }

    function populateAgentSelect() {
        const defaults = state.meta.defaults || {};
        elements.agentSelect.innerHTML = '';

        state.meta.agents.forEach(function(agent) {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = agent.name;
            if (agent.id === defaults.agent_id) {
                option.selected = true;
            }
            elements.agentSelect.appendChild(option);
        });

        if (!elements.agentSelect.value && state.meta.agents.length > 0) {
            elements.agentSelect.value = state.meta.agents[0].id;
        }
        updateModelSuggestions();
    }

    function updateModelSuggestions() {
        const agentMeta = findAgentMeta(elements.agentSelect.value);
        const models = agentMeta ? agentMeta.models || [] : [];
        const currentModelId = elements.modelSelect.value;

        elements.modelSelect.innerHTML = '';

        function appendOption(value, label, options) {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = label;
            if (options && options.disabled) {
                option.disabled = true;
            }
            if (options && options.selected) {
                option.selected = true;
            }
            elements.modelSelect.appendChild(option);
        }

        if (!agentMeta) {
            appendOption('', '等待加载模型列表', { disabled: true, selected: true });
            setModelHint('');
            elements.refreshModelsButton.disabled = true;
            return;
        }

        elements.refreshModelsButton.disabled = false;

        if (models.length === 0) {
            appendOption('', '暂无可用模型', { disabled: true, selected: true });
            setModelHint(agentMeta.model_error || '当前 Agent 还没有配置模型，请点击刷新模型');
            return;
        }

        models.forEach(function(model) {
            appendOption(model.id, model.label || model.id);
        });
        if (currentModelId && models.some(function(model) {
            return model.id === currentModelId;
        })) {
            elements.modelSelect.value = currentModelId;
        }
        setModelHint('');
    }

    function upsertAgentMeta(agentMeta) {
        if (!state.meta || !agentMeta) {
            return;
        }
        state.meta.agents = state.meta.agents
            .filter(function(agent) {
                return agent.id !== agentMeta.id;
            })
            .concat([agentMeta])
            .sort(function(left, right) {
                return String(left.name || left.id).localeCompare(String(right.name || right.id), 'zh-CN');
            });
    }

    async function loadMeta() {
        const response = await fetch('/api/meta');
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || '加载元数据失败');
        }

        state.meta = payload;
        populateHubSelect();
        populateAgentSelect();
    }

    async function refreshSelectedAgentModels() {
        const agentId = String(elements.agentSelect.value || '').trim();
        if (!agentId) {
            showToast('请先选择 Agent', 'error');
            return;
        }

        const originalText = elements.refreshModelsButton.textContent;
        elements.refreshModelsButton.disabled = true;
        elements.refreshModelsButton.classList.add('is-loading');
        elements.refreshModelsButton.textContent = '刷新中...';

        try {
            const response = await fetch(`/api/agents/${encodeURIComponent(agentId)}/models/refresh`, {
                method: 'POST'
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || '刷新模型失败');
            }

            upsertAgentMeta(payload);
            updateModelSuggestions();
            showToast(`已刷新 ${payload.models ? payload.models.length : 0} 个模型，并写入配置文件`, 'success');
        } catch (error) {
            showToast(error.message || String(error), 'error');
        } finally {
            elements.refreshModelsButton.disabled = false;
            elements.refreshModelsButton.classList.remove('is-loading');
            elements.refreshModelsButton.textContent = originalText;
        }
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

    function jumpToPage(force) {
        const page = Number.parseInt(elements.pageJumpInput.value, 10);
        if (Number.isNaN(page)) {
            if (force) {
                elements.pageJumpInput.value = String(state.page);
            }
            return;
        }

        const target = Math.min(state.totalPages, Math.max(1, page));
        if (target === state.page) {
            elements.pageJumpInput.value = String(state.page);
            return;
        }

        state.page = target;
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

    function renderRecords(records) {
        state.records = records;

        if (!records.length) {
            elements.recordsTableBody.innerHTML = '<tr><td colspan="7" class="empty-row">还没有检视记录，先发起一个任务吧。</td></tr>';
            return;
        }

        elements.recordsTableBody.innerHTML = records.map(function(record) {
            const mrTitle = record.title || record.mr_url;
            const queueHint = record.runtime_state === 'queued' && record.queue_position
                ? `排队第 ${record.queue_position} 位`
                : (record.runtime_state === 'running' ? '后台执行中' : '已结束');

            return `
                <tr>
                    <td>#${record.id}</td>
                    <td>
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(mrTitle)}</div>
                            <a class="record-link" href="${escapeHtml(record.mr_url)}" target="_blank" rel="noreferrer">${escapeHtml(record.mr_url)}</a>
                        </div>
                    </td>
                    <td>${escapeHtml(record.hub_id)}</td>
                    <td>
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(record.agent_id)}</div>
                            <div class="record-subtitle">${escapeHtml(record.model_id)}</div>
                        </div>
                    </td>
                    <td>
                        ${renderStatusPill(record)}
                        <div class="record-subtitle">${escapeHtml(queueHint)}</div>
                    </td>
                    <td>
                        <div class="record-time">创建：${escapeHtml(formatDate(record.created_at))}</div>
                        <div class="record-time">开始：${escapeHtml(formatDate(record.started_at))}</div>
                    </td>
                    <td>
                        <div class="record-actions">
                            <button type="button" class="table-action-button" data-view-review-id="${record.id}">查看详情</button>
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
        const response = await fetch(`/api/reviews?${params.toString()}`);
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || '加载记录失败');
        }

        renderRecords(payload.records || []);
        renderPagination(payload.pagination || {});

        if (state.openDetailId != null && !elements.detailModal.hidden) {
            await loadDetail(state.openDetailId, true);
        }
    }

    function renderDetail(detail) {
        state.openDetailId = detail.id;
        state.openDetailRecord = detail;
        elements.detailStatusPill.className = `status-pill ${getStatusClass(detail)}`;
        elements.detailStatusPill.textContent = detail.status_label;
        elements.detailContent.hidden = false;

        elements.detailId.textContent = `#${detail.id}`;
        elements.detailQueuePosition.textContent = detail.queue_position ? `第 ${detail.queue_position} 位` : '-';
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
        elements.detailWorkingDirectory.textContent = detail.working_directory || '-';
        elements.detailCommand.textContent = detail.command_line || '-';
        elements.detailResult.textContent = detail.result_text || detail.error_message || '-';
        elements.detailLogs.textContent = (detail.logs || []).map(function(item) {
            return item.line;
        }).join('\n') || '-';

        openDetailModal();
    }

    async function loadDetail(reviewId, silent) {
        const response = await fetch(`/api/reviews/${reviewId}`);
        const payload = await response.json();
        if (!response.ok) {
            if (!silent) {
                throw new Error(payload.error || '加载详情失败');
            }
            return;
        }
        renderDetail(payload);
    }

    async function submitReview(event) {
        event.preventDefault();
        const payload = {
            mr_url: elements.mrUrlInput.value.trim(),
            hub_id: elements.hubSelect.value,
            agent_id: elements.agentSelect.value,
            model_id: elements.modelSelect.value.trim()
        };

        if (!payload.mr_url) {
            showToast('请先填写 MR 检视地址', 'error');
            elements.mrUrlInput.focus();
            return;
        }

        if (!payload.model_id) {
            showToast('请先选择模型', 'error');
            elements.modelSelect.focus();
            return;
        }

        elements.submitButton.disabled = true;
        elements.submitButton.textContent = '提交中...';
        try {
            const response = await fetch('/api/reviews', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || '创建检视任务失败');
            }

            showToast(`检视任务 #${result.id} 已加入队列`, 'success');
            elements.reviewForm.reset();
            populateHubSelect();
            populateAgentSelect();
            state.page = 1;
            await refreshReviews();
        } catch (error) {
            showToast(error.message || String(error), 'error');
        } finally {
            elements.submitButton.disabled = false;
            elements.submitButton.textContent = '加入检视队列';
        }
    }

    function prefillReviewForm(record) {
        if (!record || !record.mr_url) {
            showToast('未找到可回填的 MR 地址', 'error');
            return;
        }

        elements.mrUrlInput.value = record.mr_url;
        if (!elements.detailModal.hidden) {
            closeDetailModal();
        }

        window.requestAnimationFrame(function() {
            elements.mrUrlInput.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            elements.mrUrlInput.focus();
        });

        showToast('已回填 MR 地址，请重新选择 Agent 和模型后再发起检视', 'success');
    }

    function bindEvents() {
        elements.agentSelect.addEventListener('change', function() {
            updateModelSuggestions();
        });
        elements.refreshModelsButton.addEventListener('click', function() {
            refreshSelectedAgentModels().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.reviewForm.addEventListener('submit', submitReview);
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
    }

    async function bootstrap() {
        cacheElements();
        if (window.initThemeToggle) {
            window.initThemeToggle();
        }
        bindEvents();
        await loadMeta();
        setAutoRefresh(false);
        await refreshReviews();
    }

    document.addEventListener('DOMContentLoaded', function() {
        bootstrap().catch(function(error) {
            showToast(error.message || String(error), 'error');
        });
    });
})();
