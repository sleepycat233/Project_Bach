/**
 * ModelSelector - AI模型选择组件
 * 处理语言选择、模型配置和智能推荐功能
 */

import { ApiClient, LoadingManager, NotificationManager } from '../shared.js';

export class ModelSelector {
    constructor(options = {}) {
        this.options = {
            languageSelectId: 'languageSelect',
            modelSelectId: 'modelSelect',
            modelInfoId: 'modelInfoContent',
            contentTypeSelectName: 'content_type',
            apiEndpoint: '/api/models/smart-config',
            ...options
        };

        this.apiClient = new ApiClient();
        this.loadingManager = new LoadingManager();
        this.notifications = new NotificationManager();
        this.modelsConfig = {
            english: [],
            multilingual: [],
            contentTypes: {},
            all: []
        };

        this.init();
    }

    init() {
        this.languageSelect = document.getElementById(this.options.languageSelectId);
        this.modelSelect = document.getElementById(this.options.modelSelectId);
        this.modelInfo = document.getElementById(this.options.modelInfoId);
        this.contentTypeSelect = document.querySelector(`select[name="${this.options.contentTypeSelectName}"]`);

        if (!this.languageSelect || !this.modelSelect) {
            console.warn('ModelSelector: Required elements not found');
            return;
        }

        this.setupEventListeners();
        this.loadModelsConfig();
    }

    setupEventListeners() {
        // 语言选择变化
        this.languageSelect.addEventListener('change', () => {
            this.updateModelOptions();
        });

        // 模型选择变化
        this.modelSelect.addEventListener('change', () => {
            this.updateModelInfo();
        });

        // 内容类型变化（如果存在）
        if (this.contentTypeSelect) {
            this.contentTypeSelect.addEventListener('change', () => {
                this.updateModelOptions();
            });
        }
    }

    async loadModelsConfig() {
        const loader = this.loadingManager.show(this.modelSelect.parentElement, 'Loading models...');

        try {
            const response = await this.apiClient.get(this.options.apiEndpoint);
            
            if (response.data.error) {
                throw new Error(response.data.error);
            }

            // 处理API返回的数据格式
            this.modelsConfig = {
                // 英文模式：显示英文推荐模型和通用模型
                english: response.data.all ? response.data.all.filter(m => 
                    m.language_mode === 'english' || m.language_mode === 'general'
                ) : [],
                
                // 多语言模式：显示多语言推荐模型和通用模型
                multilingual: response.data.all ? response.data.all.filter(m => 
                    m.language_mode === 'multilingual' || m.language_mode === 'general'
                ) : [],
                
                contentTypes: {
                    lecture: response.data.lecture || [],
                    meeting: response.data.meeting || [],
                    others: response.data.others || []
                },
                
                all: response.data.all || []
            };

            // 为每个语言模式的模型设置推荐状态和排序
            this.processModelRecommendations();

            console.log('Models config loaded:', this.modelsConfig);

            // 更新UI
            this.updateModelOptions();
            
        } catch (error) {
            console.error('Error loading models config:', error);
            this.notifications.error(`Failed to load models: ${error.message}`);
            this.showErrorState(error.message);
        } finally {
            if (loader && loader.hide) {
                loader.hide();
            }
        }
    }

    processModelRecommendations() {
        // 处理英文模式模型
        this.modelsConfig.english = this.modelsConfig.english.map(model => {
            const updatedModel = {...model};
            updatedModel.recommended = model.is_english_recommended === true;
            return updatedModel;
        }).sort((a, b) => {
            // 推荐模型排在前面
            if (a.recommended && !b.recommended) return -1;
            if (!a.recommended && b.recommended) return 1;
            return 0;
        });

        // 处理多语言模式模型
        this.modelsConfig.multilingual = this.modelsConfig.multilingual.map(model => {
            const updatedModel = {...model};
            updatedModel.recommended = model.is_multilingual_recommended === true;
            return updatedModel;
        }).sort((a, b) => {
            // 推荐模型排在前面
            if (a.recommended && !b.recommended) return -1;
            if (!a.recommended && b.recommended) return 1;
            return 0;
        });
    }

    updateModelOptions() {
        const language = this.languageSelect.value;
        const contentType = this.contentTypeSelect ? this.contentTypeSelect.value : '';

        // 获取适用的模型列表
        let models = this.getModelsForContext(language, contentType);

        // 清除现有选项
        this.modelSelect.innerHTML = '';

        if (models.length === 0) {
            this.showLoadingState();
            return;
        }

        // 添加模型选项
        let selectedModel = null;
        models.forEach((model, index) => {
            const option = document.createElement('option');
            option.value = model.value;
            
            // 构建选项显示文本
            let optionText = model.display_name || model.name;
            
            // 为推荐模型添加星星标记
            if (model.recommended) {
                optionText = optionText + ' ⭐';
            }
            
            // 特殊处理需要安装的模型
            if (model.status === 'install_required') {
                optionText = '📦 ' + optionText;
            }
            
            option.textContent = optionText;
            
            // 智能选择逻辑
            if (!selectedModel) {
                if (model.recommended) {
                    selectedModel = option;
                } else if (index === 0) {
                    selectedModel = option;
                }
            } else if (model.recommended && !selectedModel.textContent.includes('⭐')) {
                selectedModel = option;
            }
            
            this.modelSelect.appendChild(option);
        });

        // 应用选择
        if (selectedModel) {
            selectedModel.selected = true;
        }

        this.updateModelInfo();
    }

    getModelsForContext(language, contentType) {
        let models = [];

        // 优先使用内容类型专用模型
        if (contentType && this.modelsConfig.contentTypes[contentType]) {
            const contentTypeModels = this.modelsConfig.contentTypes[contentType];
            models = contentTypeModels.filter(model => {
                const isRecommended = language === 'english' 
                    ? model.is_english_recommended 
                    : model.is_multilingual_recommended;
                
                // 设置推荐标志
                model.recommended = language === 'english' 
                    ? model.is_english_recommended 
                    : model.is_multilingual_recommended;
                
                // MLX模型都支持双语，无需额外过滤
                return true;
            });
        } else {
            // 回退到全局语言模型
            console.log(`🔍 Using fallback global models for language: ${language}`);
            models = this.modelsConfig[language] || [];
        }

        return models;
    }

    updateModelInfo() {
        const language = this.languageSelect.value;
        const modelValue = this.modelSelect.value;
        const models = this.modelsConfig[language] || this.modelsConfig.english;
        const selectedModel = models.find(m => m.value === modelValue);

        if (selectedModel && this.modelInfo) {
            this.displayModelInfo(selectedModel);
            this.checkModelAvailability(selectedModel.value);
        }
    }

    displayModelInfo(model) {
        const configInfo = model.config_info || {};
        const encoderLayers = configInfo.encoder_layers || 0;
        const decoderLayers = configInfo.decoder_layers || 0;
        const dModel = configInfo.d_model || 0;
        const modelSize = model.model_size || 'Unknown';

        this.modelInfo.innerHTML = `
            <div style="margin-bottom: 15px;">
                <div style="margin-bottom: 8px;">
                    <strong style="color: #667eea; font-size: 1.1em;">${model.display_name || model.name}</strong>
                </div>
                <div style="display: flex; gap: 20px; font-size: 0.9em; color: #495057; margin-bottom: 10px;">
                    <div><strong>📦 Size:</strong> ${modelSize}</div>
                    ${model.provider ? `<div><strong>🔗 Provider:</strong> ${model.provider}</div>` : ''}
                </div>
                ${(encoderLayers || decoderLayers || dModel) ? `
                <div style="font-size: 0.85rem; color: #666; margin-top: 8px;">
                    <div><strong>📊 Model Architecture:</strong></div>
                    <div style="margin-left: 15px; margin-top: 4px;">
                        ${encoderLayers ? `• Encoder: ${encoderLayers} layers<br>` : ''}
                        ${decoderLayers ? `• Decoder: ${decoderLayers} layers<br>` : ''}
                        ${dModel ? `• Hidden size: ${dModel}` : ''}
                    </div>
                </div>
                ` : ''}
            </div>
            <div style="margin-top: 8px; padding: 6px 10px; border-radius: 4px; font-size: 0.8rem; background: #f8f9fa; border: 1px solid #dee2e6;">
                📊 <strong>Performance Benchmarks:</strong> 
                <a href="https://huggingface.co/spaces/argmaxinc/whisperkit-benchmarks" target="_blank" style="color: #667eea; text-decoration: none;">
                    View WhisperKit Benchmarks →
                </a>
            </div>
            <div id="modelStatus" style="margin-top: 8px; padding: 6px 10px; border-radius: 4px; font-size: 0.8rem;">
                <!-- Model availability status will be shown here -->
            </div>
        `;
    }

    checkModelAvailability(modelValue) {
        const statusDiv = this.modelInfo.querySelector('#modelStatus');
        if (!statusDiv) return;

        // 特殊处理需要安装的模型
        if (modelValue === 'install_required') {
            statusDiv.innerHTML = `
                <div style="color: #856404;">📦 No models installed for this language mode</div>
                <div style="font-size: 0.85rem; margin-top: 5px; font-family: monospace; background: #f8f9fa; padding: 8px; border-radius: 4px;">
                    Install models using:<br>
                    <code>whisperkit-cli download --model large-v3 --model-prefix distil</code> (English)<br>
                    <code>whisperkit-cli download --model large-v3 --model-prefix openai</code> (Multilingual)
                </div>
            `;
            statusDiv.style.background = '#fff3cd';
            statusDiv.style.color = '#856404';
            return;
        }

        // 其他模型被认为是已下载可用的
        statusDiv.innerHTML = '';
        statusDiv.style.background = 'transparent';
        statusDiv.style.color = 'inherit';
    }

    showLoadingState() {
        this.modelSelect.innerHTML = '<option value="" disabled>Loading models...</option>';
    }

    showErrorState(message) {
        this.modelSelect.innerHTML = `<option value="" disabled>Error: ${message}</option>`;
    }

    // 公共方法
    getSelectedModel() {
        const modelValue = this.modelSelect.value;
        const language = this.languageSelect.value;
        const models = this.modelsConfig[language] || [];
        return models.find(m => m.value === modelValue);
    }

    getSelectedLanguage() {
        return this.languageSelect.value;
    }

    getAllModels() {
        return this.modelsConfig;
    }

    setLanguage(language) {
        if (this.languageSelect.value !== language) {
            this.languageSelect.value = language;
            this.updateModelOptions();
        }
    }

    setModel(modelValue) {
        if (this.modelSelect.value !== modelValue) {
            this.modelSelect.value = modelValue;
            this.updateModelInfo();
        }
    }

    refresh() {
        this.loadModelsConfig();
    }

    reset() {
        this.languageSelect.selectedIndex = 0;
        this.updateModelOptions();
    }

    // 事件监听器
    onModelChanged(callback) {
        this.modelSelect.addEventListener('change', callback);
    }

    onLanguageChanged(callback) {
        this.languageSelect.addEventListener('change', callback);
    }

    offModelChanged(callback) {
        this.modelSelect.removeEventListener('change', callback);
    }

    offLanguageChanged(callback) {
        this.languageSelect.removeEventListener('change', callback);
    }
}

// 全局注册组件
if (typeof window !== 'undefined') {
    window.ModelSelector = ModelSelector;
}