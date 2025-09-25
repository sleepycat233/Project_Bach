/**
 * StatusTracker - 状态跟踪组件
 * 处理处理状态监控、进度显示和实时更新功能
 */

import { ApiClient, timeUtils } from '../shared.js';

export class StatusTracker {
    constructor(options = {}) {
        this.options = {
            containerId: 'status-container',
            apiEndpoint: '/api/status/processing',
            refreshInterval: 10000, // 10秒
            autoStart: true,
            showProgress: true,
            showTimestamp: true,
            maxRetries: 3,
            retryDelay: 5000,
            ...options
        };

        this.apiClient = new ApiClient();
        this.isActive = false;
        this.intervalId = null;
        this.retryCount = 0;
        this.lastUpdate = null;
        this.statusHistory = [];

        if (this.options.autoStart) {
            this.init();
        }
    }

    init() {
        this.container = document.getElementById(this.options.containerId);
        if (!this.container) {
            console.warn('StatusTracker: Container element not found');
            return;
        }

        this.setupUI();
        this.start();
    }

    setupUI() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="status-header">
                <h3>Processing Status</h3>
                <div class="status-controls">
                    <button id="status-refresh-btn" class="btn btn-secondary" title="Refresh Status">
                        🔄 Refresh
                    </button>
                    <button id="status-toggle-btn" class="btn btn-secondary" title="Toggle Auto-refresh">
                        ⏸️ Pause
                    </button>
                </div>
            </div>
            <div id="status-content" class="status-content">
                <div class="status-loading">
                    <div class="loading-spinner"></div>
                    <span>Loading status...</span>
                </div>
            </div>
            <div class="status-footer">
                <small id="status-last-update" class="status-timestamp">Never updated</small>
            </div>
        `;

        this.setupEventListeners();
    }

    setupEventListeners() {
        const refreshBtn = document.getElementById('status-refresh-btn');
        const toggleBtn = document.getElementById('status-toggle-btn');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.fetchStatus();
            });
        }

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                if (this.isActive) {
                    this.stop();
                    toggleBtn.innerHTML = '▶️ Resume';
                    toggleBtn.title = 'Resume Auto-refresh';
                } else {
                    this.start();
                    toggleBtn.innerHTML = '⏸️ Pause';
                    toggleBtn.title = 'Pause Auto-refresh';
                }
            });
        }

        // 页面可见性变化处理
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pause();
            } else if (this.isActive) {
                this.resume();
            }
        });
    }

    async fetchStatus() {
        try {
            const response = await this.apiClient.get(this.options.apiEndpoint);
            const payload = response.data || {};

            if (!payload.success) {
                throw new Error(payload.error || 'Failed to fetch status');
            }

            const statusData = payload.data?.active_sessions ?? [];

            this.handleStatusUpdate(statusData);
            this.retryCount = 0; // 重置重试计数
        } catch (error) {
            console.error('StatusTracker: Failed to fetch status', error);
            this.handleError(error);
        }
    }

    handleStatusUpdate(data) {
        this.lastUpdate = new Date();
        const historyEntry = Array.isArray(data) ? { sessions: data } : { ...data };
        historyEntry.timestamp = this.lastUpdate;
        this.statusHistory.unshift(historyEntry);
        
        // 限制历史记录长度
        if (this.statusHistory.length > 50) {
            this.statusHistory.pop();
        }

        this.updateUI(data);
        this.updateTimestamp();
        
        // 触发状态更新事件
        this.triggerStatusUpdateEvent(data);
    }

    updateUI(status) {
        const contentDiv = document.getElementById('status-content');
        if (!contentDiv) return;

        if (!status || Object.keys(status).length === 0) {
            contentDiv.innerHTML = this.renderEmptyState();
            return;
        }

        // 根据状态类型渲染不同的UI
        if (Array.isArray(status)) {
            contentDiv.innerHTML = this.renderStatusList(status);
        } else if (status.current_task || status.queue) {
            contentDiv.innerHTML = this.renderDetailedStatus(status);
        } else {
            contentDiv.innerHTML = this.renderSimpleStatus(status);
        }
    }

    renderEmptyState() {
        return `
            <div class="status-empty">
                <div class="empty-icon">📝</div>
                <div class="empty-title">No Processing Tasks</div>
                <div class="empty-description">All tasks completed or no tasks in queue</div>
            </div>
        `;
    }

    renderStatusList(statusList) {
        if (statusList.length === 0) {
            return this.renderEmptyState();
        }

        return `
            <div class="status-list">
                ${statusList.map((item, index) => `
                    <div class="status-item ${item.status || item.stage || 'unknown'}">
                        <div class="status-item-header">
                            <span class="status-icon">${this.getStatusIcon(item.status || item.stage)}</span>
                            <span class="status-title">${item.name || item.filename || item.processing_id || `Task ${index + 1}`}</span>
                            <span class="status-badge ${item.status || item.stage || 'unknown'}">${(item.status || item.stage || 'Unknown').toString().toUpperCase()}</span>
                        </div>
                        ${item.progress !== undefined ? `
                            <div class="status-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${item.progress || 0}%"></div>
                                </div>
                                <span class="progress-text">${item.progress || 0}%</span>
                            </div>
                        ` : ''}
                        ${item.message ? `
                            <div class="status-message">${item.message}</div>
                        ` : ''}
                        ${item.created_at || item.started_at ? `
                            <div class="status-time">
                                Started: ${timeUtils.timeAgo(item.created_at || item.started_at)}
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderDetailedStatus(status) {
        return `
            <div class="detailed-status">
                ${status.current_task ? `
                    <div class="current-task">
                        <div class="task-header">
                            <span class="task-icon">${this.getStatusIcon(status.current_task.status)}</span>
                            <div class="task-info">
                                <div class="task-title">${status.current_task.name || 'Current Task'}</div>
                                <div class="task-status">${status.current_task.status || 'Processing'}</div>
                            </div>
                        </div>
                        ${status.current_task.progress !== undefined ? `
                            <div class="task-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${status.current_task.progress}%"></div>
                                </div>
                                <span class="progress-text">${status.current_task.progress}%</span>
                            </div>
                        ` : ''}
                        ${status.current_task.message ? `
                            <div class="task-message">${status.current_task.message}</div>
                        ` : ''}
                    </div>
                ` : ''}
                
                ${status.queue && status.queue.length > 0 ? `
                    <div class="queue-section">
                        <div class="queue-header">
                            <span>Queue (${status.queue.length} items)</span>
                        </div>
                        <div class="queue-items">
                            ${status.queue.slice(0, 5).map(item => `
                                <div class="queue-item">
                                    <span class="queue-icon">📄</span>
                                    <span class="queue-name">${item.name || item.filename || 'Queued Task'}</span>
                                </div>
                            `).join('')}
                            ${status.queue.length > 5 ? `
                                <div class="queue-more">... and ${status.queue.length - 5} more</div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
                
                ${status.stats ? `
                    <div class="status-stats">
                        <div class="stats-grid">
                            ${status.stats.completed ? `
                                <div class="stat-item">
                                    <div class="stat-value">${status.stats.completed}</div>
                                    <div class="stat-label">Completed</div>
                                </div>
                            ` : ''}
                            ${status.stats.failed ? `
                                <div class="stat-item">
                                    <div class="stat-value">${status.stats.failed}</div>
                                    <div class="stat-label">Failed</div>
                                </div>
                            ` : ''}
                            ${status.stats.total_time ? `
                                <div class="stat-item">
                                    <div class="stat-value">${timeUtils.formatDuration(status.stats.total_time)}</div>
                                    <div class="stat-label">Total Time</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderSimpleStatus(status) {
        return `
            <div class="simple-status">
                <div class="status-card">
                    <div class="status-icon">${this.getStatusIcon(status.status || status.stage)}</div>
                    <div class="status-info">
                        <div class="status-title">${status.message || 'Processing'}</div>
                        <div class="status-details">
                            ${status.filename ? `File: ${status.filename}` : ''}
                            ${status.progress !== undefined ? ` • Progress: ${status.progress}%` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getStatusIcon(status) {
        const icons = {
            pending: '⏳',
            processing: '🔄',
            completed: '✅',
            success: '✅',
            failed: '❌',
            error: '❌',
            cancelled: '⏹️',
            paused: '⏸️',
            uploaded: '📤',
            transcribing: '🗣️',
            anonymizing: '🕵️',
            ai_generating: '🤖',
            publishing: '🚀',
            unknown: '❓'
        };
        return icons[status] || icons.unknown;
    }

    updateTimestamp() {
        const timestampEl = document.getElementById('status-last-update');
        if (timestampEl && this.lastUpdate) {
            timestampEl.textContent = `Last updated: ${timeUtils.timeAgo(this.lastUpdate)}`;
        }
    }

    handleError(error) {
        this.retryCount++;
        
        if (this.retryCount <= this.options.maxRetries) {
            console.log(`StatusTracker: Retrying in ${this.options.retryDelay / 1000}s (${this.retryCount}/${this.options.maxRetries})`);
            setTimeout(() => {
                this.fetchStatus();
            }, this.options.retryDelay);
        } else {
            this.showErrorState(error);
            this.retryCount = 0; // 重置重试计数，下次更新时重新开始
        }
    }

    showErrorState(error) {
        const contentDiv = document.getElementById('status-content');
        if (!contentDiv) return;

        contentDiv.innerHTML = `
            <div class="status-error">
                <div class="error-icon">⚠️</div>
                <div class="error-title">Failed to Load Status</div>
                <div class="error-message">${error.message || 'Unknown error occurred'}</div>
                <button id="status-retry-btn" class="btn btn-primary" style="margin-top: var(--spacing-md);">
                    🔄 Retry
                </button>
            </div>
        `;

        // 添加重试按钮事件
        const retryBtn = document.getElementById('status-retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.retryCount = 0;
                this.fetchStatus();
            });
        }
    }

    triggerStatusUpdateEvent(status) {
        const event = new CustomEvent('statusUpdated', {
            detail: {
                status,
                timestamp: this.lastUpdate,
                history: this.statusHistory
            }
        });
        document.dispatchEvent(event);
    }

    // 控制方法
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.fetchStatus(); // 立即获取一次
        
        this.intervalId = setInterval(() => {
            this.fetchStatus();
        }, this.options.refreshInterval);
        
        console.log('StatusTracker: Started auto-refresh');
    }

    stop() {
        if (!this.isActive) return;
        
        this.isActive = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        
        console.log('StatusTracker: Stopped auto-refresh');
    }

    pause() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    resume() {
        if (this.isActive && !this.intervalId) {
            this.intervalId = setInterval(() => {
                this.fetchStatus();
            }, this.options.refreshInterval);
        }
    }

    // 公共方法
    isRunning() {
        return this.isActive;
    }

    getLastStatus() {
        return this.statusHistory[0] || null;
    }

    getStatusHistory() {
        return [...this.statusHistory];
    }

    setRefreshInterval(interval) {
        this.options.refreshInterval = interval;
        if (this.isActive) {
            this.stop();
            this.start();
        }
    }

    clearHistory() {
        this.statusHistory = [];
    }

    destroy() {
        this.stop();
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    // 事件监听器
    onStatusUpdate(callback) {
        document.addEventListener('statusUpdated', callback);
    }

    offStatusUpdate(callback) {
        document.removeEventListener('statusUpdated', callback);
    }
}

// 全局注册组件
if (typeof window !== 'undefined') {
    window.StatusTracker = StatusTracker;
}
