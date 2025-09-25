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
            availableApiEndpoint: '/api/models/available',
            recommendationsApiEndpoint: '/api/preferences/recommendations/_all',
            defaultContentType: null,
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
        if (this.options.contentTypeSelectName) {
            this.contentTypeSelect = document.querySelector(`select[name="${this.options.contentTypeSelectName}"]`);
        } else {
            this.contentTypeSelect = null;
        }
        this.defaultContentType = this.options.defaultContentType;

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
            const [modelsResponse, recommendationsResponse] = await Promise.all([
                this.apiClient.get(this.options.availableApiEndpoint),
                this.apiClient.get(this.options.recommendationsApiEndpoint)
            ]);

            const modelsPayload = modelsResponse.data || {};
            const recommendationsPayload = recommendationsResponse.data || {};

            if (!modelsPayload.success) {
                throw new Error(modelsPayload.error || 'Failed to load available models');
            }

            if (!recommendationsPayload.success) {
                throw new Error(recommendationsPayload.error || 'Failed to load recommendations');
            }

            const baseModels = modelsPayload.data?.models || [];
            const recommendationData = recommendationsPayload.data || {};
            const requestedContentTypes = recommendationData.ordered_content_types || [];
            const recommendationMap = recommendationData.recommendations || {};
            const globalEnglishSet = new Set(recommendationData.all?.english || []);
            const globalMultilingualSet = new Set(recommendationData.all?.multilingual || []);

            const allModels = this.sortModels(
                baseModels.map(model => this.buildModelEntry(model, globalEnglishSet, globalMultilingualSet))
            );

            const englishModels = this.prepareLanguageModels(allModels, 'english');
            const multilingualModels = this.prepareLanguageModels(allModels, 'multilingual');

            const contentTypeModels = {};
            const effectiveContentTypes = requestedContentTypes.length > 0
                ? requestedContentTypes
                : Object.keys(recommendationMap);

            effectiveContentTypes.forEach(contentType => {
                const recs = recommendationMap[contentType] || {};
                const englishSet = new Set(recs.english || []);
                const multilingualSet = new Set(recs.multilingual || []);
                contentTypeModels[contentType] = this.sortModels(
                    baseModels.map(model => this.buildModelEntry(model, englishSet, multilingualSet))
                );
            });

            this.modelsConfig = {
                english: englishModels,
                multilingual: multilingualModels,
                contentTypes: {
                    lecture: contentTypeModels.lecture || [],
                    meeting: contentTypeModels.meeting || [],
                    others: contentTypeModels.others || [],
                    ...contentTypeModels
                },
                all: allModels
            };

            console.log('Models config loaded:', this.modelsConfig);

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

    buildModelEntry(model, englishSet, multilingualSet) {
        const value = model.value || model.name;
        const entry = { ...model };
        entry.is_english_recommended = englishSet.has(value);
        entry.is_multilingual_recommended = multilingualSet.has(value);

        if (entry.is_english_recommended && !entry.is_multilingual_recommended) {
            entry.language_mode = 'english';
        } else if (entry.is_multilingual_recommended && !entry.is_english_recommended) {
            entry.language_mode = 'multilingual';
        } else {
            entry.language_mode = 'general';
        }

        entry.recommended = false;
        entry.config_info = entry.config_info || {};
        return entry;
    }

    prepareLanguageModels(allModels, language) {
        return allModels
            .filter(model =>
                language === 'english'
                    ? (model.language_mode === 'english' || model.language_mode === 'general')
                    : (model.language_mode === 'multilingual' || model.language_mode === 'general')
            )
            .map(model => ({
                ...model,
                recommended: language === 'english'
                    ? model.is_english_recommended === true
                    : model.is_multilingual_recommended === true
            }));
    }

    sortModels(models) {
        return [...models].sort((a, b) => {
            const aRecommended = a.is_english_recommended || a.is_multilingual_recommended;
            const bRecommended = b.is_english_recommended || b.is_multilingual_recommended;
            if (aRecommended !== bRecommended) {
                return aRecommended ? -1 : 1;
            }

            if (a.is_default && !b.is_default) return -1;
            if (!a.is_default && b.is_default) return 1;

            const aName = (a.display_name || a.name || '').toString();
            const bName = (b.display_name || b.name || '').toString();
            return aName.localeCompare(bName);
        });
    }

    updateModelOptions() {
        const language = this.languageSelect.value;
        const contentType = this.contentTypeSelect ? this.contentTypeSelect.value : (this.defaultContentType || '');

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
        if (contentType && this.modelsConfig.contentTypes[contentType] && this.modelsConfig.contentTypes[contentType].length > 0) {
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
        }
        
        // 如果没有content type特定模型或为空，回退到全局语言模型
        if (models.length === 0) {
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
