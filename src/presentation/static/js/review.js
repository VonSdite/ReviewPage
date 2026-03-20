(function() {
    const state = {
        meta: null,
        records: [],
        selectedReviewId: null,
        refreshTimer: null
    };

    const elements = {};

    function cacheElements() {
        elements.reviewForm = document.getElementById('reviewForm');
        elements.mrUrlInput = document.getElementById('mrUrlInput');
        elements.hubSelect = document.getElementById('hubSelect');
        elements.agentSelect = document.getElementById('agentSelect');
        elements.modelInput = document.getElementById('modelInput');
        elements.modelSuggestions = document.getElementById('modelSuggestions');
        elements.modelHint = document.getElementById('modelHint');
        elements.refreshButton = document.getElementById('refreshButton');
        elements.submitButton = document.getElementById('submitButton');
        elements.recordsTableBody = document.getElementById('recordsTableBody');
        elements.detailEmpty = document.getElementById('detailEmpty');
        elements.detailContent = document.getElementById('detailContent');
        elements.detailStatusPill = document.getElementById('detailStatusPill');
        elements.detailRetryButton = document.getElementById('detailRetryButton');
        elements.toastStack = document.getElementById('toastStack');
        elements.workerHint = document.getElementById('workerHint');

        elements.metricTotal = document.getElementById('metricTotal');
        elements.metricQueued = document.getElementById('metricQueued');
        elements.metricRunning = document.getElementById('metricRunning');
        elements.metricCompleted = document.getElementById('metricCompleted');
        elements.metricFailed = document.getElementById('metricFailed');

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
        const statusClass = getStatusClass(record);
        const label = record ? record.status_label : '未选择';
        return `<span class="status-pill ${statusClass}">${escapeHtml(label)}</span>`;
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

        elements.modelSuggestions.innerHTML = '';
        models.forEach(function(model) {
            const option = document.createElement('option');
            option.value = model.id;
            option.label = model.label || model.id;
            elements.modelSuggestions.appendChild(option);
        });

        if (models.length > 0 && !elements.modelInput.value) {
            elements.modelInput.value = models[0].id;
        }

        if (!agentMeta) {
            elements.modelHint.textContent = '等待加载 Agent 模型列表';
            return;
        }

        if (agentMeta.models.length === 0) {
            elements.modelHint.textContent = agentMeta.model_error || '当前 Agent 没有可选模型，请手动输入';
            return;
        }

        let hint = `已加载 ${agentMeta.models.length} 个模型，来源：${agentMeta.model_source}`;
        if (agentMeta.model_error) {
            hint += `，附带提示：${agentMeta.model_error}`;
        }
        elements.modelHint.textContent = hint;
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

    function renderStats(stats) {
        elements.metricTotal.textContent = String(stats.total || 0);
        elements.metricQueued.textContent = String(stats.queued || 0);
        elements.metricRunning.textContent = String(stats.running || 0);
        elements.metricCompleted.textContent = String(stats.completed || 0);
        elements.metricFailed.textContent = String(stats.failed || 0);

        if ((stats.running || 0) > 0) {
            elements.workerHint.textContent = '后台当前有检视任务正在执行';
        } else if ((stats.queued || 0) > 0) {
            elements.workerHint.textContent = '后台当前为空闲，队列中仍有待执行任务';
        } else {
            elements.workerHint.textContent = '后台空闲，可继续提交检视任务';
        }
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
                : (record.runtime_state === 'running' ? '后台执行中' : '已完成');

            return `
                <tr data-review-id="${record.id}" class="${record.id === state.selectedReviewId ? 'is-active' : ''}">
                    <td>#${record.id}</td>
                    <td>
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(mrTitle)}</div>
                            <a class="record-link" href="${escapeHtml(record.mr_url)}" target="_blank" rel="noreferrer">${escapeHtml(record.mr_url)}</a>
                        </div>
                    </td>
                    <td>${escapeHtml(record.hub_name || record.hub_id)}</td>
                    <td>
                        <div class="record-meta">
                            <div class="record-title">${escapeHtml(record.agent_name || record.agent_id)}</div>
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
                            <button
                                type="button"
                                class="retry-inline-button"
                                data-retry-review-id="${record.id}"
                            >重来</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function refreshReviews(options) {
        const keepSelection = !options || options.keepSelection !== false;
        const response = await fetch('/api/reviews?limit=100');
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || '加载记录失败');
        }

        renderStats(payload.stats || {});
        renderRecords(payload.records || []);

        if (keepSelection && state.selectedReviewId != null) {
            const exists = state.records.some(function(record) {
                return record.id === state.selectedReviewId;
            });
            if (exists) {
                await loadDetail(state.selectedReviewId, true);
                return;
            }
            state.selectedReviewId = null;
        }

        if (state.selectedReviewId == null && state.records.length > 0) {
            await loadDetail(state.records[0].id, true);
        }
    }

    function setDetailVisibility(hasDetail) {
        elements.detailEmpty.hidden = hasDetail;
        elements.detailContent.hidden = !hasDetail;
    }

    function renderDetail(detail) {
        state.selectedReviewId = detail.id;
        elements.detailStatusPill.className = `status-pill ${getStatusClass(detail)}`;
        elements.detailStatusPill.textContent = detail.status_label;
        elements.detailRetryButton.disabled = !detail.can_retry;
        setDetailVisibility(true);

        elements.detailId.textContent = `#${detail.id}`;
        elements.detailQueuePosition.textContent = detail.queue_position ? `第 ${detail.queue_position} 位` : '-';
        elements.detailMrUrl.textContent = detail.mr_url || '-';
        elements.detailMrUrl.href = detail.mr_url || '#';
        elements.detailHub.textContent = detail.hub_name || detail.hub_id || '-';
        elements.detailAgent.textContent = detail.agent_name || detail.agent_id || '-';
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

        renderRecords(state.records);
    }

    async function retryReview(reviewId, triggerButton) {
        if (!Number.isFinite(reviewId)) {
            return;
        }

        const button = triggerButton || null;
        const originalText = button ? button.textContent : '';

        if (button) {
            button.disabled = true;
            button.classList.add('is-loading');
            button.textContent = '重来中...';
        }
        if (elements.detailRetryButton && Number(state.selectedReviewId) === reviewId && elements.detailRetryButton !== button) {
            elements.detailRetryButton.disabled = true;
        }

        try {
            const response = await fetch(`/api/reviews/${reviewId}/retry`, {
                method: 'POST'
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || '重来任务创建失败');
            }

            showToast(`已基于任务 #${reviewId} 新建检视任务 #${result.id}`, 'success');
            await refreshReviews({ keepSelection: false });
            await loadDetail(result.id, true);
        } catch (error) {
            showToast(error.message || String(error), 'error');
            if (state.selectedReviewId != null) {
                await loadDetail(state.selectedReviewId, true);
            }
        } finally {
            if (button) {
                button.disabled = false;
                button.classList.remove('is-loading');
                button.textContent = originalText || '重来';
            }
        }
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
            model_id: elements.modelInput.value.trim()
        };

        if (!payload.mr_url) {
            showToast('请先填写 MR 检视地址', 'error');
            elements.mrUrlInput.focus();
            return;
        }

        if (!payload.model_id) {
            showToast('请先选择或输入模型', 'error');
            elements.modelInput.focus();
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
            await refreshReviews({ keepSelection: false });
            await loadDetail(result.id, true);
        } catch (error) {
            showToast(error.message || String(error), 'error');
        } finally {
            elements.submitButton.disabled = false;
            elements.submitButton.textContent = '加入检视队列';
        }
    }

    function bindEvents() {
        elements.agentSelect.addEventListener('change', function() {
            elements.modelInput.value = '';
            updateModelSuggestions();
        });

        elements.reviewForm.addEventListener('submit', submitReview);
        elements.refreshButton.addEventListener('click', function() {
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.detailRetryButton.addEventListener('click', function() {
            if (state.selectedReviewId == null) {
                return;
            }
            retryReview(Number(state.selectedReviewId), elements.detailRetryButton).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });

        elements.recordsTableBody.addEventListener('click', function(event) {
            const retryButton = event.target.closest('[data-retry-review-id]');
            if (retryButton) {
                event.stopPropagation();
                const reviewId = Number(retryButton.getAttribute('data-retry-review-id'));
                retryReview(reviewId, retryButton).catch(function(error) {
                    showToast(error.message || String(error), 'error');
                });
                return;
            }

            const row = event.target.closest('tr[data-review-id]');
            if (!row) {
                return;
            }

            const reviewId = Number(row.getAttribute('data-review-id'));
            if (!Number.isFinite(reviewId)) {
                return;
            }

            loadDetail(reviewId).catch(function(error) {
                showToast(error.message || String(error), 'error');
            });
        });
    }

    async function bootstrap() {
        cacheElements();
        if (window.initThemeToggle) {
            window.initThemeToggle();
        }
        bindEvents();
        await loadMeta();
        await refreshReviews();

        state.refreshTimer = window.setInterval(function() {
            refreshReviews().catch(function(error) {
                showToast(error.message || String(error), 'error');
                if (state.refreshTimer) {
                    window.clearInterval(state.refreshTimer);
                    state.refreshTimer = null;
                }
            });
        }, 4000);
    }

    document.addEventListener('DOMContentLoaded', function() {
        bootstrap().catch(function(error) {
            showToast(error.message || String(error), 'error');
        });
    });
})();
