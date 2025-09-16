/**
 * ConfigManager - 前端配置管理工具
 * 从后端API获取配置并应用到前端组件
 */

export class ConfigManager {
    constructor() {
        this.config = null;
        this.isLoading = false;
        this.isLoaded = false;
    }

    async loadConfig() {
        if (this.isLoading || this.isLoaded) {
            return this.config;
        }

        this.isLoading = true;

        try {
            const response = await fetch('/api/config/frontend');
            const result = await response.json();

            if (result.success && result.data) {
                this.config = result.data;
                this.isLoaded = true;
                console.log('Frontend config loaded:', this.config);

                // 自动更新页面中的动态文本
                this.updateDynamicElements();

                return this.config;
            } else {
                throw new Error('Failed to load frontend config');
            }
        } catch (error) {
            console.warn('Error loading frontend config:', error);
            // 使用默认配置
            this.config = {
                upload: {
                    max_file_size: 1073741824,
                    max_file_size_display: '1GB',
                    allowed_extensions: ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'aac', 'ogg']
                }
            };
            this.isLoaded = true;
            return this.config;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * 自动更新页面中标记了 data-config-* 属性的元素
     */
    updateDynamicElements() {
        if (!this.config) return;

        // 更新文件大小显示
        const maxSizeElements = document.querySelectorAll('[data-config-max-size]');
        maxSizeElements.forEach(element => {
            const template = element.getAttribute('data-config-max-size');
            element.textContent = template.replace('{{MAX_SIZE}}', this.config.upload.max_file_size_display);
        });

        // 更新支持的格式列表
        const formatsElements = document.querySelectorAll('[data-config-formats]');
        formatsElements.forEach(element => {
            const template = element.getAttribute('data-config-formats');
            const formats = this.config.upload.allowed_extensions.map(ext => ext.toUpperCase()).join(', ');
            element.textContent = template.replace('{{FORMATS}}', formats);
        });

        // 更新组合的格式和大小信息
        const combinedElements = document.querySelectorAll('[data-config-combined]');
        combinedElements.forEach(element => {
            const template = element.getAttribute('data-config-combined');
            const formats = this.config.upload.allowed_extensions.map(ext => ext.toUpperCase()).join(', ');
            let text = template.replace('{{FORMATS}}', formats);
            text = text.replace('{{MAX_SIZE}}', this.config.upload.max_file_size_display);
            element.textContent = text;
        });
    }

    /**
     * 获取上传配置
     */
    getUploadConfig() {
        return this.config?.upload || {
            max_file_size: 1073741824,
            max_file_size_display: '1GB',
            allowed_extensions: ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'aac', 'ogg']
        };
    }
}

// 全局单例实例
const configManager = new ConfigManager();

// 页面加载时自动加载配置
document.addEventListener('DOMContentLoaded', () => {
    configManager.loadConfig();
});

export default configManager;