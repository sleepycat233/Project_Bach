/**
 * YouTubeHandler - YouTube URL处理和元数据获取组件
 * 处理YouTube链接验证、元数据获取和内容建议功能
 */

import { urlUtils, ApiClient, LoadingManager, debounce } from '../shared.js';

export class YouTubeHandler {
    constructor(options = {}) {
        this.options = {
            urlInputId: 'youtube-url-input',
            contextSuggestionsId: 'context-suggestions',
            contextTextareaId: 'youtube-context',
            loadingIndicatorId: 'youtube-loading-indicator',
            cancelButtonId: 'youtube-cancel-button',
            autoFetchDelay: 800,
            ...options
        };

        this.apiClient = new ApiClient();
        this.loadingManager = new LoadingManager();
        this.currentMetadata = null;
        this.currentRequest = null;
        this.loadingIndicator = null;

        this.init();
    }

    init() {
        this.urlInput = document.getElementById(this.options.urlInputId);
        this.contextSuggestions = document.getElementById(this.options.contextSuggestionsId);
        this.contextTextarea = document.getElementById(this.options.contextTextareaId);
        this.indicator = document.getElementById(this.options.loadingIndicatorId);
        this.cancelButton = document.getElementById(this.options.cancelButtonId);

        if (!this.urlInput) {
            console.warn('YouTubeHandler: URL input element not found');
            return;
        }

        this.setupEventListeners();
        this.initializeLoadingIndicator();
    }

    setupEventListeners() {
        // URL输入防抖处理
        const debouncedHandler = debounce((url) => {
            this.handleUrlChange(url);
        }, this.options.autoFetchDelay);

        this.urlInput.addEventListener('input', (e) => {
            const url = e.target.value.trim();
            debouncedHandler(url);
        });

        // 取消按钮
        if (this.cancelButton) {
            this.cancelButton.addEventListener('click', () => {
                this.cancelCurrentRequest();
            });
        }

        // 监听取消事件
        document.addEventListener('youtube-metadata-cancelled', (event) => {
            console.log('YouTube metadata request cancelled:', event.detail.message);
        });
    }

    initializeLoadingIndicator() {
        this.loadingIndicator = new YouTubeLoadingIndicator({
            indicatorId: this.options.loadingIndicatorId,
            cancelButtonId: this.options.cancelButtonId
        });
    }

    handleUrlChange(url) {
        if (url.length === 0) {
            this.hideLoadingIndicator();
            this.hideSuggestions();
            return;
        }

        // 如果正在加载，取消之前的请求
        if (this.loadingIndicator && this.loadingIndicator.isLoading()) {
            this.loadingIndicator.hide();
        }

        // 验证YouTube URL
        if (this.isValidYouTubeUrl(url)) {
            console.log('Valid YouTube URL detected, fetching metadata');
            this.fetchVideoMetadata(url);
        } else if (url.length > 10) {
            // 如果URL长度足够但格式不对，显示错误
            this.showError('Please enter a valid YouTube URL');
        }
    }

    isValidYouTubeUrl(url) {
        return urlUtils.isValidYouTubeUrl(url);
    }

    async fetchVideoMetadata(url) {
        // 显示加载状态
        this.showSuggestions();
        this.showLoading();

        if (this.loadingIndicator) {
            this.loadingIndicator.showLoading();
        }

        // 创建AbortController用于取消请求
        const abortController = new AbortController();
        this.currentRequest = {
            abort: () => abortController.abort(),
            url: url,
            startTime: Date.now()
        };

        if (this.loadingIndicator) {
            this.loadingIndicator.setCurrentRequest(this.currentRequest);
        }

        try {
            const response = await this.apiClient.get(
                `/api/youtube/metadata?url=${encodeURIComponent(url)}`,
                { signal: abortController.signal }
            );

            if (response.data && response.data.title) {
                this.currentMetadata = response.data;
                this.displaySuggestions(response.data);
                this.hideLoading();

                if (this.loadingIndicator) {
                    this.loadingIndicator.showSuccess();
                }

                // 触发元数据获取成功事件
                this.triggerEvent('metadataLoaded', { metadata: response.data, url });
            } else {
                throw new Error(response.data?.error || 'Failed to fetch video metadata');
            }
        } catch (error) {
            console.error('Error fetching video metadata:', error);
            this.hideLoading();

            if (error.name === 'AbortError') {
                this.showError('Request cancelled by user');
            } else {
                this.showError(error.message || 'Failed to fetch video metadata');
            }

            if (this.loadingIndicator && error.name !== 'AbortError') {
                this.loadingIndicator.showError(error.message);
            }

            // 触发元数据获取失败事件
            this.triggerEvent('metadataError', { error, url });
        } finally {
            this.currentRequest = null;
            if (this.loadingIndicator) {
                this.loadingIndicator.setCurrentRequest(null);
            }
        }
    }

    displaySuggestions(metadata) {
        if (!this.contextSuggestions) return;

        const titleSuggestion = this.contextSuggestions.querySelector('#suggestion-title');
        const descriptionSuggestion = this.contextSuggestions.querySelector('#suggestion-description');
        const combinedSuggestion = this.contextSuggestions.querySelector('#suggestion-combined');

        // 显示标题建议
        if (metadata.title && titleSuggestion) {
            const titleText = titleSuggestion.querySelector('#video-title-text');
            if (titleText) {
                titleText.textContent = metadata.title;
            }
            titleSuggestion.style.display = 'block';

            const titleContent = titleSuggestion.querySelector('.suggestion-content');
            if (titleContent) {
                titleContent.onclick = () => {
                    this.fillContext(metadata.title);
                    this.highlightSelected(titleContent);
                };
            }
        }

        // 显示描述建议
        if (metadata.description && descriptionSuggestion) {
            const descriptionText = descriptionSuggestion.querySelector('#video-description-text');
            if (descriptionText) {
                descriptionText.textContent = metadata.description;
            }
            descriptionSuggestion.style.display = 'block';

            const descriptionContent = descriptionSuggestion.querySelector('.suggestion-content');
            if (descriptionContent) {
                descriptionContent.onclick = () => {
                    this.fillContext(metadata.description);
                    this.highlightSelected(descriptionContent);
                };
            }
        }

        // 显示组合建议
        if ((metadata.title || metadata.description) && combinedSuggestion) {
            combinedSuggestion.style.display = 'block';

            const combinedContent = combinedSuggestion.querySelector('.suggestion-content');
            if (combinedContent) {
                combinedContent.onclick = () => {
                    const combinedText = [
                        metadata.title ? `Title: ${metadata.title}` : '',
                        metadata.description ? `Description: ${metadata.description}` : ''
                    ].filter(Boolean).join('\n\n');

                    this.fillContext(combinedText);
                    this.highlightSelected(combinedContent);
                };
            }
        }
    }

    fillContext(text) {
        if (!this.contextTextarea) return;

        const currentValue = this.contextTextarea.value.trim();
        if (currentValue) {
            if (confirm('Replace existing context with the suggestion?')) {
                this.contextTextarea.value = text;
            }
        } else {
            this.contextTextarea.value = text;
        }

        // 滚动到Context文本框并聚焦
        this.contextTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
        this.contextTextarea.focus();

        // 触发内容填入事件
        this.triggerEvent('contextFilled', { text, source: 'suggestion' });
    }

    highlightSelected(selectedElement) {
        // 移除其他建议的高亮
        this.contextSuggestions.querySelectorAll('.suggestion-content').forEach(elem => {
            elem.style.background = 'white';
            elem.style.borderColor = '#dee2e6';
        });

        // 高亮当前选中的建议
        selectedElement.style.background = '#e8f5e8';
        selectedElement.style.borderColor = '#28a745';

        // 3秒后恢复正常样式
        setTimeout(() => {
            selectedElement.style.background = 'white';
            selectedElement.style.borderColor = '#dee2e6';
        }, 3000);
    }

    showSuggestions() {
        if (this.contextSuggestions) {
            this.contextSuggestions.style.display = 'block';
        }
    }

    hideSuggestions() {
        if (this.contextSuggestions) {
            this.contextSuggestions.style.display = 'none';
            // 隐藏所有建议项
            this.contextSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                item.style.display = 'none';
            });
        }
    }

    showLoading() {
        const loadingDiv = this.contextSuggestions?.querySelector('#metadata-loading');
        const errorDiv = this.contextSuggestions?.querySelector('#metadata-error');

        if (loadingDiv) loadingDiv.style.display = 'block';
        if (errorDiv) errorDiv.style.display = 'none';

        // 隐藏所有建议项
        this.contextSuggestions?.querySelectorAll('.suggestion-item').forEach(item => {
            item.style.display = 'none';
        });
    }

    hideLoading() {
        const loadingDiv = this.contextSuggestions?.querySelector('#metadata-loading');
        if (loadingDiv) loadingDiv.style.display = 'none';
    }

    showError(message) {
        const errorDiv = this.contextSuggestions?.querySelector('#metadata-error');
        if (errorDiv) {
            errorDiv.textContent = `❌ ${message}`;
            errorDiv.style.display = 'block';
        }
        this.hideLoading();
    }

    showLoadingIndicator() {
        if (this.loadingIndicator) {
            this.loadingIndicator.showLoading();
        }
    }

    hideLoadingIndicator() {
        if (this.loadingIndicator) {
            this.loadingIndicator.hide();
        }
    }

    cancelCurrentRequest() {
        if (this.currentRequest) {
            console.log('Cancelling YouTube metadata request');
            this.currentRequest.abort();
            this.currentRequest = null;

            if (this.loadingIndicator) {
                this.loadingIndicator.hide();
            }

            this.triggerEvent('requestCancelled', { message: 'User cancelled the request' });
            return true;
        }
        return false;
    }

    triggerEvent(eventName, detail = {}) {
        const event = new CustomEvent(`youtube-${eventName}`, { detail });
        document.dispatchEvent(event);
    }

    // 公共方法
    getCurrentMetadata() {
        return this.currentMetadata;
    }

    isLoading() {
        return this.currentRequest !== null;
    }

    getVideoId() {
        if (!this.currentMetadata) return null;
        return urlUtils.extractYouTubeId(this.urlInput.value);
    }

    reset() {
        this.urlInput.value = '';
        this.currentMetadata = null;
        this.hideSuggestions();
        this.hideLoadingIndicator();
        if (this.contextTextarea) {
            this.contextTextarea.value = '';
        }
    }

    // 事件监听器
    onMetadataLoaded(callback) {
        document.addEventListener('youtube-metadataLoaded', callback);
    }

    onMetadataError(callback) {
        document.addEventListener('youtube-metadataError', callback);
    }

    onContextFilled(callback) {
        document.addEventListener('youtube-contextFilled', callback);
    }

    onRequestCancelled(callback) {
        document.addEventListener('youtube-requestCancelled', callback);
    }
}

/**
 * YouTube加载指示器类
 */
class YouTubeLoadingIndicator {
    constructor(options = {}) {
        this.options = {
            indicatorId: 'youtube-loading-indicator',
            cancelButtonId: 'youtube-cancel-button',
            ...options
        };

        this.indicator = document.getElementById(this.options.indicatorId);
        this.cancelButton = document.getElementById(this.options.cancelButtonId);
        this.currentState = 'hidden';
        this.currentRequest = null;

        this.setupEventListeners();
    }

    setupEventListeners() {
        if (this.cancelButton) {
            this.cancelButton.addEventListener('click', () => {
                this.cancel();
            });
        }
    }

    showLoading() {
        if (!this.indicator) return;

        this.currentState = 'loading';
        this.indicator.className = 'youtube-loading-indicator loading';
        this.indicator.setAttribute('aria-label', 'Loading YouTube metadata, please wait');
        this.indicator.setAttribute('aria-live', 'polite');

        // 创建旋转指示器
        const spinnerContainer = document.createElement('div');
        spinnerContainer.className = 'spinner';
        this.indicator.innerHTML = '';
        this.indicator.appendChild(spinnerContainer);

        // 显示取消按钮
        if (this.cancelButton) {
            this.cancelButton.classList.add('visible');
        }
    }

    showSuccess() {
        if (!this.indicator) return;

        this.currentState = 'success';
        this.indicator.className = 'youtube-loading-indicator success';
        this.indicator.setAttribute('aria-label', 'YouTube metadata loaded successfully');
        this.indicator.innerHTML = '<div class="success-icon">✓</div>';

        if (this.cancelButton) {
            this.cancelButton.classList.remove('visible');
        }

        // 3秒后自动隐藏
        setTimeout(() => this.hide(), 3000);
    }

    showError(message = 'Error loading metadata') {
        if (!this.indicator) return;

        this.currentState = 'error';
        this.indicator.className = 'youtube-loading-indicator error';
        this.indicator.setAttribute('aria-label', `Error loading YouTube metadata: ${message}`);
        this.indicator.setAttribute('role', 'alert');
        this.indicator.innerHTML = '<div class="error-icon">✕</div>';

        if (this.cancelButton) {
            this.cancelButton.classList.remove('visible');
        }

        // 5秒后自动隐藏
        setTimeout(() => this.hide(), 5000);
    }

    hide() {
        if (!this.indicator) return;

        this.currentState = 'hidden';
        this.indicator.className = 'youtube-loading-indicator hidden';
        this.indicator.innerHTML = '';

        if (this.cancelButton) {
            this.cancelButton.classList.remove('visible');
        }
    }

    cancel() {
        if (this.currentState === 'loading' && this.currentRequest) {
            if (this.currentRequest.abort) {
                this.currentRequest.abort();
            }

            this.currentRequest = null;
            this.hide();

            const cancelEvent = new CustomEvent('youtube-metadata-cancelled', {
                detail: { message: 'User cancelled the request' }
            });
            document.dispatchEvent(cancelEvent);

            return true;
        }
        return false;
    }

    setCurrentRequest(request) {
        this.currentRequest = request;
    }

    getCurrentState() {
        return this.currentState;
    }

    isLoading() {
        return this.currentState === 'loading';
    }
}

// 全局注册组件
if (typeof window !== 'undefined') {
    window.YouTubeHandler = YouTubeHandler;
    window.YouTubeLoadingIndicator = YouTubeLoadingIndicator;
}