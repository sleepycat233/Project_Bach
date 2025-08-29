/**
 * Project Bach - Web App JavaScript
 * 专用于Web应用的交互功能和组件集成
 */

import { 
    ApiClient, 
    NotificationManager, 
    LoadingManager, 
    FormValidator,
    DarkModeManager 
} from './shared.js';

import { FileUploadComponent } from './components/FileUploadComponent.js';
import { YouTubeHandler } from './components/YouTubeHandler.js';
import { ModelSelector } from './components/ModelSelector.js';
import { TabManager } from './components/TabManager.js';
import { StatusTracker } from './components/StatusTracker.js';

/**
 * Web应用主控制器
 */
class WebApp {
    constructor() {
        this.apiClient = new ApiClient();
        this.notifications = new NotificationManager();
        this.loadingManager = new LoadingManager();
        this.darkModeManager = new DarkModeManager();
        
        this.components = {};
        this.forms = {};
        
        this.init();
    }

    init() {
        this.initializeComponents();
        this.setupForms();
        this.setupGlobalEventHandlers();
        this.loadInitialData();
        
        console.log('Web App initialized');
    }

    initializeComponents() {
        // 标签管理器
        this.components.tabManager = new TabManager({
            defaultTab: 'audio',
            onTabChange: (newTab, previousTab) => {
                this.handleTabChange(newTab, previousTab);
            }
        });

        // 文件上传组件
        this.components.fileUpload = new FileUploadComponent({
            dropZoneId: 'audio-drop-zone',
            fileInputId: 'audio-file-input',
            allowedExtensions: ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'aac', 'ogg']
        });

        // YouTube处理组件
        this.components.youtubeHandler = new YouTubeHandler({
            urlInputId: 'youtube-url-input',
            contextSuggestionsId: 'context-suggestions',
            contextTextareaId: 'youtube-context'
        });

        // 模型选择器 - Audio标签页
        this.components.modelSelector = new ModelSelector({
            languageSelectId: 'languageSelect',
            modelSelectId: 'modelSelect',
            modelInfoId: 'modelInfoContent'
        });

        // 模型选择器 - YouTube标签页
        this.components.youtubeModelSelector = new ModelSelector({
            languageSelectId: 'youtubeLanguageSelect',
            modelSelectId: 'youtubeModelSelect',
            modelInfoId: 'youtubeModelInfoContent'
        });

        // 状态跟踪器
        this.components.statusTracker = new StatusTracker({
            containerId: 'status-container',
            autoStart: true
        });

        this.setupComponentInteractions();
    }

    setupComponentInteractions() {
        // 文件上传事件
        this.components.fileUpload.onFilesChanged((event) => {
            const { files, count } = event.detail;
            console.log(`Files selected: ${count}`, files);
            
            if (count > 0) {
                this.components.tabManager.enableTab('audio-processing');
            }
        });

        // YouTube元数据加载事件
        this.components.youtubeHandler.onMetadataLoaded((event) => {
            const { metadata, url } = event.detail;
            console.log('YouTube metadata loaded:', metadata);
            
            this.notifications.success('Video information loaded successfully');
            this.components.tabManager.enableTab('youtube-processing');
        });

        // 模型选择变化
        this.components.modelSelector.onModelChanged(() => {
            const selectedModel = this.components.modelSelector.getSelectedModel();
            console.log('Model changed:', selectedModel);
            
            this.updateProcessingOptions(selectedModel);
        });

        // 状态更新
        this.components.statusTracker.onStatusUpdate((event) => {
            const { status } = event.detail;
            this.handleStatusUpdate(status);
        });
    }

    setupForms() {
        this.setupAudioForm();
        this.setupYouTubeForm();
        this.setupConfigForm();
    }

    setupAudioForm() {
        const form = document.getElementById('audio-form');
        if (!form) return;

        const validator = new FormValidator();
        validator.required('content_type', 'Please select a content type');

        this.forms.audio = {
            element: form,
            validator: validator
        };

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleAudioFormSubmission(form, validator);
        });

        // 子分类选择处理
        this.setupSubcategorySelection();
    }

    setupYouTubeForm() {
        const form = document.getElementById('youtube-form');
        if (!form) return;

        const validator = new FormValidator();
        validator.required('url', 'Please enter a YouTube URL')
               .url('url', 'Please enter a valid YouTube URL');

        this.forms.youtube = {
            element: form,
            validator: validator
        };

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleYouTubeFormSubmission(form, validator);
        });
    }

    setupConfigForm() {
        const form = document.getElementById('config-form');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleConfigFormSubmission(form);
        });
    }

    setupSubcategorySelection() {
        const contentTypeSelect = document.querySelector('select[name="content_type"]');
        const subcategoryContainer = document.getElementById('subcategory-container');
        
        if (!contentTypeSelect || !subcategoryContainer) return;

        // 初始化：检查默认选中的content type
        const initialType = contentTypeSelect.value;
        if (initialType) {
            this.updateSubcategoryOptions(initialType);
        }

        contentTypeSelect.addEventListener('change', async (e) => {
            const selectedType = e.target.value;
            await this.updateSubcategoryOptions(selectedType);
        });

        // 处理自定义子分类
        const subcategorySelect = document.getElementById('subcategory-select');
        const customInput = document.getElementById('custom-subcategory-input');
        
        if (subcategorySelect && customInput) {
            subcategorySelect.addEventListener('change', (e) => {
                const isCustom = e.target.value === 'other';
                customInput.style.display = isCustom ? 'block' : 'none';
                customInput.required = isCustom;
            });
        }
    }

    async updateSubcategoryOptions(contentType) {
        try {
            const response = await this.apiClient.get('/api/categories');
            const contentTypeData = response.data[contentType];
            
            const subcategoryContainer = document.getElementById('subcategory-container');
            const subcategorySelect = document.getElementById('subcategory-select');
            const subcategoryLabel = document.getElementById('subcategory-label');
            
            if (contentTypeData?.subcategories?.length > 0) {
                subcategoryContainer.style.display = 'block';
                subcategoryLabel.textContent = contentType === 'lecture' ? 'Course Selection' : 'Subcategory';
                
                // 清空并重新填充选项
                subcategorySelect.innerHTML = '<option value="">Select a ' + 
                    (contentType === 'lecture' ? 'course' : 'subcategory') + '...</option>';
                
                contentTypeData.subcategories.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub;
                    option.textContent = sub;
                    subcategorySelect.appendChild(option);
                });
                
                // 添加"其他"选项
                const otherOption = document.createElement('option');
                otherOption.value = 'other';
                otherOption.textContent = 'Other (specify below)';
                subcategorySelect.appendChild(otherOption);
                
            } else {
                subcategoryContainer.style.display = 'none';
                document.getElementById('custom-subcategory-input').style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading subcategories:', error);
        }
    }

    async handleAudioFormSubmission(form, validator) {
        const validation = validator.validateForm(form);
        
        if (!validation.isValid) {
            validator.showErrors(validation.errors, form);
            return;
        }

        const messageDiv = document.getElementById('audio-upload-message');
        const loader = this.loadingManager.show('audio-form', 'Uploading file...');

        try {
            const formData = new FormData(form);
            const response = await this.apiClient.post('/upload/audio', formData);

            if (response.redirected) {
                this.notifications.success('Audio file uploaded successfully!');
                setTimeout(() => {
                    window.location.href = response.url;
                }, 1000);
            } else {
                this.notifications.success(response.data.message || 'Upload successful!');
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.notifications.error('Upload failed: ' + error.message);
        } finally {
            loader.hide();
        }
    }

    async handleYouTubeFormSubmission(form, validator) {
        const validation = validator.validateForm(form);
        
        if (!validation.isValid) {
            validator.showErrors(validation.errors, form);
            return;
        }

        const loader = this.loadingManager.show('youtube-form', 'Processing YouTube URL...');

        try {
            const formData = new FormData(form);
            const response = await this.apiClient.post('/upload/youtube', formData);

            if (response.redirected) {
                this.notifications.success('YouTube URL submitted successfully!');
                setTimeout(() => {
                    window.location.href = response.url;
                }, 1000);
            } else {
                this.notifications.success(response.data.message || 'Submission successful!');
            }

        } catch (error) {
            console.error('YouTube submission error:', error);
            this.notifications.error('Submission failed: ' + error.message);
        } finally {
            loader.hide();
        }
    }

    async handleConfigFormSubmission(form) {
        const loader = this.loadingManager.show('config-form', 'Saving configuration...');

        try {
            const formData = new FormData(form);
            const response = await this.apiClient.post('/api/config/save', formData);

            this.notifications.success('Configuration saved successfully');
            
        } catch (error) {
            console.error('Config save error:', error);
            this.notifications.error('Failed to save configuration: ' + error.message);
        } finally {
            loader.hide();
        }
    }

    handleTabChange(newTab, previousTab) {
        console.log(`Tab changed from ${previousTab} to ${newTab}`);

        // 根据标签切换调整UI
        if (newTab === 'audio' && this.components.fileUpload) {
            this.components.fileUpload.refresh?.();
        } else if (newTab === 'youtube' && this.components.youtubeHandler) {
            // YouTube标签特定初始化
        }
    }

    handleStatusUpdate(status) {
        // 根据状态更新UI
        if (status?.current_task?.status === 'completed') {
            this.notifications.success('Task completed successfully!');
        } else if (status?.current_task?.status === 'failed') {
            this.notifications.error('Task failed: ' + (status.current_task.message || 'Unknown error'));
        }
    }

    updateProcessingOptions(model) {
        // 根据选择的模型更新处理选项
        const processingOptions = document.getElementById('processing-options');
        if (processingOptions && model) {
            // 显示模型相关的选项
        }
    }

    async loadInitialData() {
        // 加载初始数据
        try {
            const [categoriesResponse] = await Promise.allSettled([
                this.apiClient.get('/api/categories')
            ]);

            if (categoriesResponse.status === 'fulfilled') {
                this.contentTypes = categoriesResponse.value.data;
            }

        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    setupGlobalEventHandlers() {
        // 全局键盘快捷键
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case '1':
                        e.preventDefault();
                        this.components.tabManager.switchTab('audio');
                        break;
                    case '2':
                        e.preventDefault();
                        this.components.tabManager.switchTab('youtube');
                        break;
                }
            }
        });

        // 页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.components.statusTracker?.pause?.();
            } else {
                this.components.statusTracker?.resume?.();
            }
        });

        // 在线状态变化
        window.addEventListener('online', () => {
            this.notifications.success('Connection restored');
        });

        window.addEventListener('offline', () => {
            this.notifications.warning('Connection lost. Some features may not work.');
        });
    }

    // 公共方法
    getComponent(name) {
        return this.components[name];
    }

    getForm(name) {
        return this.forms[name];
    }

    refresh() {
        Object.values(this.components).forEach(component => {
            if (component.refresh) {
                component.refresh();
            }
        });
    }

    destroy() {
        Object.values(this.components).forEach(component => {
            if (component.destroy) {
                component.destroy();
            }
        });
        
        this.components = {};
        this.forms = {};
    }
}

// 初始化Web应用
document.addEventListener('DOMContentLoaded', () => {
    window.webApp = new WebApp();
});

// 导出模块
export { WebApp };