/**
 * Project Bach - Shared JavaScript Utilities
 * 通用JavaScript工具函数和常用功能
 */

// ===== 工具函数 =====

/**
 * API请求工具类，提供统一的错误处理和加载状态管理
 */
export class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * 通用fetch请求包装器
     * @param {string} url - 请求URL
     * @param {Object} options - 请求选项
     * @returns {Promise} 请求响应
     */
    async request(url, options = {}) {
        const fullUrl = this.baseUrl + url;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        try {
            const response = await fetch(fullUrl, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            // 检查是否为重定向响应
            if (response.redirected) {
                return { redirected: true, url: response.url, response };
            }

            const data = await response.json();
            return { data, response };
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // HTTP方法便捷函数
    async get(url, options = {}) {
        return this.request(url, { method: 'GET', ...options });
    }

    async post(url, data, options = {}) {
        const body = data instanceof FormData ? data : JSON.stringify(data);
        const headers = data instanceof FormData ? {} : this.defaultHeaders;
        return this.request(url, {
            method: 'POST',
            body,
            headers: { ...headers, ...options.headers },
            ...options
        });
    }

    async put(url, data, options = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
            ...options
        });
    }

    async delete(url, options = {}) {
        return this.request(url, { method: 'DELETE', ...options });
    }
}

/**
 * 消息通知系统
 */
export class NotificationManager {
    constructor(containerId = 'notifications') {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.createContainer(containerId);
        }
    }

    createContainer(id) {
        this.container = document.createElement('div');
        this.container.id = id;
        this.container.className = 'notifications-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--color-${type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'primary'});
            border-radius: var(--border-radius-md);
            padding: var(--spacing-md);
            margin-bottom: var(--spacing-sm);
            box-shadow: var(--shadow-md);
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            cursor: pointer;
        `;

        const content = document.createElement('div');
        content.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: var(--spacing-sm);">
                <span style="font-size: 1.2em; flex-shrink: 0;">
                    ${type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}
                </span>
                <div style="flex: 1; color: var(--text-primary); line-height: 1.4;">
                    ${message}
                </div>
                <button style="background: none; border: none; font-size: 1.2em; color: var(--text-secondary); cursor: pointer; padding: 0; line-height: 1;">×</button>
            </div>
        `;

        notification.appendChild(content);
        this.container.appendChild(notification);

        // 动画显示
        requestAnimationFrame(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        });

        // 点击关闭
        const closeBtn = content.querySelector('button');
        const closeNotification = () => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        };

        closeBtn.addEventListener('click', closeNotification);
        notification.addEventListener('click', closeNotification);

        // 自动关闭
        if (duration > 0) {
            setTimeout(closeNotification, duration);
        }

        return notification;
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

/**
 * 加载状态管理器
 */
export class LoadingManager {
    constructor() {
        this.activeLoaders = new Set();
    }

    show(elementId, message = 'Loading...') {
        const element = document.getElementById(elementId);
        if (!element) return null;

        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(2px);
        `;

        loader.innerHTML = `
            <div style="text-align: center; color: var(--text-primary);">
                <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto var(--spacing-sm);"></div>
                <div style="font-size: var(--font-size-sm); font-weight: 500;">${message}</div>
            </div>
        `;

        // 确保父元素有相对定位
        if (getComputedStyle(element).position === 'static') {
            element.style.position = 'relative';
        }

        element.appendChild(loader);
        this.activeLoaders.add(loader);

        return {
            hide: () => {
                if (loader.parentNode) {
                    loader.parentNode.removeChild(loader);
                }
                this.activeLoaders.delete(loader);
            },
            updateMessage: (newMessage) => {
                const messageDiv = loader.querySelector('div div:last-child');
                if (messageDiv) {
                    messageDiv.textContent = newMessage;
                }
            }
        };
    }

    hideAll() {
        this.activeLoaders.forEach(loader => {
            if (loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
        });
        this.activeLoaders.clear();
    }
}

/**
 * 表单验证工具
 */
export class FormValidator {
    constructor() {
        this.rules = {};
        this.messages = {
            required: 'This field is required',
            email: 'Please enter a valid email address',
            url: 'Please enter a valid URL',
            minLength: 'This field must be at least {min} characters',
            maxLength: 'This field must be no more than {max} characters',
            pattern: 'This field format is invalid'
        };
    }

    addRule(fieldName, validator, message) {
        if (!this.rules[fieldName]) {
            this.rules[fieldName] = [];
        }
        this.rules[fieldName].push({ validator, message });
        return this;
    }

    required(fieldName, message) {
        return this.addRule(fieldName, (value) => value && value.trim() !== '', 
                           message || this.messages.required);
    }

    email(fieldName, message) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return this.addRule(fieldName, (value) => !value || emailPattern.test(value),
                           message || this.messages.email);
    }

    url(fieldName, message) {
        return this.addRule(fieldName, (value) => {
            if (!value) return true;
            try {
                new URL(value);
                return true;
            } catch {
                return false;
            }
        }, message || this.messages.url);
    }

    minLength(fieldName, min, message) {
        return this.addRule(fieldName, (value) => !value || value.length >= min,
                           message || this.messages.minLength.replace('{min}', min));
    }

    maxLength(fieldName, max, message) {
        return this.addRule(fieldName, (value) => !value || value.length <= max,
                           message || this.messages.maxLength.replace('{max}', max));
    }

    pattern(fieldName, regex, message) {
        return this.addRule(fieldName, (value) => !value || regex.test(value),
                           message || this.messages.pattern);
    }

    validate(formData) {
        const errors = {};
        
        for (const [fieldName, rules] of Object.entries(this.rules)) {
            const value = formData[fieldName];
            
            for (const rule of rules) {
                if (!rule.validator(value)) {
                    errors[fieldName] = rule.message;
                    break; // 只显示第一个错误
                }
            }
        }

        return {
            isValid: Object.keys(errors).length === 0,
            errors
        };
    }

    validateForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        return this.validate(data);
    }

    showErrors(errors, form) {
        // 清除之前的错误显示
        form.querySelectorAll('.form-error').forEach(el => el.remove());
        form.querySelectorAll('.form-input, .form-select, .form-textarea').forEach(el => {
            el.classList.remove('invalid');
        });

        // 显示新的错误
        for (const [fieldName, message] of Object.entries(errors)) {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.classList.add('invalid');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'form-error';
                errorDiv.style.cssText = `
                    color: var(--color-error);
                    font-size: var(--font-size-sm);
                    margin-top: var(--spacing-xs);
                `;
                errorDiv.textContent = message;
                
                field.parentNode.appendChild(errorDiv);
            }
        }
    }
}

/**
 * URL工具函数
 */
export const urlUtils = {
    /**
     * 检查是否为有效的YouTube URL
     * @param {string} url - 待检查的URL
     * @returns {boolean} 是否为有效YouTube URL
     */
    isValidYouTubeUrl(url) {
        try {
            const patterns = [
                /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
                /^https?:\/\/youtu\.be\/[\w-]+/,
                /^https?:\/\/(m\.)?youtube\.com\/watch\?v=[\w-]+/
            ];
            return patterns.some(pattern => pattern.test(url));
        } catch {
            return false;
        }
    },

    /**
     * 从YouTube URL中提取视频ID
     * @param {string} url - YouTube URL
     * @returns {string|null} 视频ID或null
     */
    extractYouTubeId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
            /youtube\.com\/embed\/([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    },

    /**
     * 检查URL是否可访问
     * @param {string} url - 待检查的URL
     * @returns {Promise<boolean>} 是否可访问
     */
    async isUrlAccessible(url) {
        try {
            const response = await fetch(url, { method: 'HEAD', mode: 'no-cors' });
            return true;
        } catch {
            return false;
        }
    }
};

/**
 * 文件工具函数
 */
export const fileUtils = {
    /**
     * 格式化文件大小
     * @param {number} bytes - 字节数
     * @returns {string} 格式化的文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * 检查文件类型是否被支持
     * @param {string} fileName - 文件名
     * @param {Array} allowedExtensions - 允许的扩展名数组
     * @returns {boolean} 是否支持
     */
    isFileTypeSupported(fileName, allowedExtensions) {
        const extension = fileName.toLowerCase().split('.').pop();
        return allowedExtensions.includes(extension);
    },

    /**
     * 获取文件扩展名
     * @param {string} fileName - 文件名
     * @returns {string} 扩展名
     */
    getFileExtension(fileName) {
        return fileName.toLowerCase().split('.').pop() || '';
    },

    /**
     * 获取文件类型图标
     * @param {string} fileName - 文件名
     * @returns {string} 图标emoji
     */
    getFileIcon(fileName) {
        const extension = this.getFileExtension(fileName);
        const iconMap = {
            // 音频文件
            mp3: '🎵', wav: '🎵', m4a: '🎵', flac: '🎵', aac: '🎵', ogg: '🎵',
            // 视频文件
            mp4: '🎬', mov: '🎬', avi: '🎬', mkv: '🎬', webm: '🎬',
            // 文档文件
            pdf: '📄', doc: '📄', docx: '📄', txt: '📄', md: '📄',
            // 图片文件
            jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', svg: '🖼️',
            // 其他
            zip: '📦', rar: '📦', tar: '📦'
        };
        return iconMap[extension] || '📎';
    }
};

/**
 * 时间工具函数
 */
export const timeUtils = {
    /**
     * 格式化时间戳为相对时间
     * @param {number|string|Date} timestamp - 时间戳
     * @returns {string} 相对时间描述
     */
    timeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        const months = Math.floor(days / 30);
        const years = Math.floor(months / 12);

        if (years > 0) return `${years} year${years > 1 ? 's' : ''} ago`;
        if (months > 0) return `${months} month${months > 1 ? 's' : ''} ago`;
        if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        return 'Just now';
    },

    /**
     * 格式化持续时间（秒）
     * @param {number} seconds - 秒数
     * @returns {string} 格式化的时间
     */
    formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
};

/**
 * 防抖函数
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 延迟时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要节流的函数
 * @param {number} limit - 时间间隔（毫秒）
 * @returns {Function} 节流后的函数
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * DOM操作工具
 */
export const domUtils = {
    /**
     * 等待元素出现在DOM中
     * @param {string} selector - CSS选择器
     * @param {number} timeout - 超时时间（毫秒）
     * @returns {Promise<Element>} 元素Promise
     */
    waitForElement(selector, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
                return;
            }

            const observer = new MutationObserver((mutations) => {
                const element = document.querySelector(selector);
                if (element) {
                    observer.disconnect();
                    resolve(element);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`Element ${selector} not found within ${timeout}ms`));
            }, timeout);
        });
    },

    /**
     * 平滑滚动到元素
     * @param {string|Element} target - 目标元素或选择器
     * @param {Object} options - 滚动选项
     */
    scrollToElement(target, options = {}) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                ...options
            });
        }
    },

    /**
     * 检查元素是否在视口中
     * @param {Element} element - 要检查的元素
     * @returns {boolean} 是否在视口中
     */
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
};

/**
 * 深色模式管理器
 */
export class DarkModeManager {
    constructor() {
        this.key = 'darkMode';
        // 已禁用自动根据系统主题切换
        // this.prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.currentMode = this.getStoredMode() || 'light'; // 默认为light模式
        this.init();
    }

    init() {
        this.applyMode(this.currentMode);
        // 已禁用系统主题监听
        // this.setupSystemListener();
        this.bindExistingButtons();
    }

    getStoredMode() {
        try {
            return localStorage.getItem(this.key);
        } catch {
            return null;
        }
    }

    setStoredMode(mode) {
        try {
            localStorage.setItem(this.key, mode);
        } catch {
            // localStorage不可用时静默失败
        }
    }

    applyMode(mode) {
        const root = document.documentElement;
        
        if (mode === 'dark') {
            root.classList.add('dark-mode');
            root.classList.remove('light-mode');
        } else {
            root.classList.add('light-mode');
            root.classList.remove('dark-mode');
        }
        
        this.currentMode = mode;
        this.updateToggleButtons();
        this.dispatchModeChange();
    }

    toggle() {
        const newMode = this.currentMode === 'dark' ? 'light' : 'dark';
        this.setMode(newMode);
    }

    setMode(mode) {
        if (mode !== 'light' && mode !== 'dark') return;
        
        this.setStoredMode(mode);
        this.applyMode(mode);
    }

    getCurrentMode() {
        return this.currentMode;
    }

    isDarkMode() {
        return this.currentMode === 'dark';
    }

    setupSystemListener() {
        // 已禁用系统偏好监听
        /*
        // 监听系统偏好变化，但只在没有手动设置时响应
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            const stored = this.getStoredMode();
            if (!stored) {
                // 只有没有手动设置时才跟随系统
                this.applyMode(e.matches ? 'dark' : 'light');
            }
        });
        */
    }

    bindExistingButtons() {
        // 绑定页面中现有的深色模式切换按钮
        const buttons = document.querySelectorAll('[data-dark-mode-toggle]');
        buttons.forEach(button => {
            // 避免重复绑定事件
            if (!button.hasAttribute('data-dark-mode-bound')) {
                button.addEventListener('click', () => {
                    this.toggle();
                });
                button.setAttribute('data-dark-mode-bound', 'true');
            }
        });
    }

    updateToggleButtons() {
        const buttons = document.querySelectorAll('[data-dark-mode-toggle]');
        buttons.forEach(button => {
            const isDark = this.isDarkMode();
            
            // 更新图标
            const icon = button.querySelector('.dark-mode-icon');
            if (icon) {
                icon.textContent = isDark ? '☀️' : '🌙';
            }
            
            // 更新文本
            const text = button.querySelector('.dark-mode-text');
            if (text) {
                text.textContent = isDark ? 'Light Mode' : 'Dark Mode';
            }
            
            // 更新aria属性
            button.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        });
    }

    dispatchModeChange() {
        const event = new CustomEvent('darkmodechange', {
            detail: { mode: this.currentMode, isDark: this.isDarkMode() }
        });
        window.dispatchEvent(event);
    }

    createToggleButton(options = {}) {
        const {
            className = 'dark-mode-toggle',
            showText = false,
            position = 'relative'
        } = options;

        const button = document.createElement('button');
        button.className = className;
        button.setAttribute('data-dark-mode-toggle', '');
        button.setAttribute('type', 'button');
        button.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius-md);
            padding: var(--spacing-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: var(--spacing-xs);
            font-family: inherit;
            font-size: var(--font-size-sm);
            color: var(--text-primary);
            transition: all 0.2s ease;
            position: ${position};
        `;

        const icon = document.createElement('span');
        icon.className = 'dark-mode-icon';
        icon.style.fontSize = '1.1em';
        button.appendChild(icon);

        if (showText) {
            const text = document.createElement('span');
            text.className = 'dark-mode-text';
            button.appendChild(text);
        }

        // 悬停效果
        button.addEventListener('mouseenter', () => {
            button.style.backgroundColor = 'var(--bg-secondary)';
            button.style.transform = 'translateY(-1px)';
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.backgroundColor = 'var(--bg-card)';
            button.style.transform = 'translateY(0)';
        });

        // 点击事件
        button.addEventListener('click', () => {
            this.toggle();
        });

        // 初始状态
        this.updateToggleButtons();

        return button;
    }
}

// 全局实例，供非模块化代码使用
if (typeof window !== 'undefined') {
    window.ProjectBach = {
        ApiClient,
        NotificationManager,
        LoadingManager,
        FormValidator,
        DarkModeManager,
        urlUtils,
        fileUtils,
        timeUtils,
        debounce,
        throttle,
        domUtils
    };

    // 创建全局通知管理器实例
    window.notifications = new NotificationManager();
    
    // 创建全局深色模式管理器实例
    window.darkMode = new DarkModeManager();
    
    // 添加全局CSS动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .notification {
            transition: all 0.3s ease;
        }
        
        .form-input.invalid,
        .form-select.invalid,
        .form-textarea.invalid {
            border-color: var(--color-error) !important;
            box-shadow: 0 0 0 3px rgba(255, 59, 48, 0.1) !important;
        }
        
        .form-error {
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
}