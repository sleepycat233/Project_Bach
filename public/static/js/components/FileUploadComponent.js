/**
 * FileUploadComponent - 文件上传组件
 * 处理拖拽上传、文件选择和验证功能
 */

import { fileUtils, NotificationManager } from '../shared.js';

export class FileUploadComponent {
    constructor(options = {}) {
        this.options = {
            dropZoneId: 'audio-drop-zone',
            fileInputId: 'audio-file-input',
            allowedExtensions: ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'aac', 'ogg'],
            maxFileSize: 500 * 1024 * 1024, // 500MB
            multipleFiles: false,
            showPreview: true,
            ...options
        };

        this.files = [];
        this.notifications = new NotificationManager();
        this.init();
    }

    init() {
        this.dropZone = document.getElementById(this.options.dropZoneId);
        this.fileInput = document.getElementById(this.options.fileInputId);

        if (!this.dropZone || !this.fileInput) {
            console.warn('FileUploadComponent: Required elements not found');
            return;
        }

        this.setupEventListeners();
        this.updateUI();
    }

    setupEventListeners() {
        // 点击上传区域打开文件选择对话框
        this.dropZone.addEventListener('click', () => {
            this.fileInput.click();
        });

        // 文件输入变化处理
        this.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(Array.from(e.target.files));
        });

        // 拖拽事件处理
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults.bind(this), false);
            document.body.addEventListener(eventName, this.preventDefaults.bind(this), false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.highlight.bind(this), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.unhighlight.bind(this), false);
        });

        this.dropZone.addEventListener('drop', this.handleDrop.bind(this), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    highlight() {
        this.dropZone.classList.add('dragover');
    }

    unhighlight() {
        this.dropZone.classList.remove('dragover');
    }

    handleDrop(e) {
        const dt = e.dataTransfer;
        const files = Array.from(dt.files);
        this.handleFileSelect(files);
    }

    handleFileSelect(files) {
        if (!files.length) return;

        const validFiles = [];
        const errors = [];

        files.forEach(file => {
            const validation = this.validateFile(file);
            if (validation.isValid) {
                validFiles.push(file);
            } else {
                errors.push(`${file.name}: ${validation.error}`);
            }
        });

        // 显示验证错误
        if (errors.length > 0) {
            this.notifications.error(
                `Some files were rejected:\n${errors.join('\n')}`,
                8000
            );
        }

        // 处理有效文件
        if (validFiles.length > 0) {
            if (this.options.multipleFiles) {
                this.files = [...this.files, ...validFiles];
            } else {
                this.files = [validFiles[0]]; // 只保留第一个文件
                this.fileInput.files = this.createFileList([validFiles[0]]);
            }

            this.updateUI();
            this.triggerChangeEvent();

            // 成功通知
            if (validFiles.length === 1) {
                this.notifications.success(`File selected: ${validFiles[0].name}`);
            } else {
                this.notifications.success(`${validFiles.length} files selected`);
            }
        }
    }

    validateFile(file) {
        // 检查文件类型
        if (!fileUtils.isFileTypeSupported(file.name, this.options.allowedExtensions)) {
            return {
                isValid: false,
                error: `Unsupported file type. Allowed: ${this.options.allowedExtensions.join(', ')}`
            };
        }

        // 检查文件大小
        if (file.size > this.options.maxFileSize) {
            return {
                isValid: false,
                error: `File too large. Maximum size: ${fileUtils.formatFileSize(this.options.maxFileSize)}`
            };
        }

        return { isValid: true };
    }

    updateUI() {
        const content = this.dropZone.querySelector('.drop-zone-content') || this.dropZone;

        if (this.files.length === 0) {
            // 显示初始状态
            content.innerHTML = `
                <span class="drop-icon">📁</span>
                <div class="drop-text">Click to select ${this.options.multipleFiles ? 'files' : 'a file'} or drag & drop</div>
                <div class="drop-hint">
                    Supported formats: ${this.options.allowedExtensions.join(', ').toUpperCase()}<br>
                    Max size: ${fileUtils.formatFileSize(this.options.maxFileSize)}
                </div>
            `;
        } else if (this.files.length === 1) {
            // 显示单个文件
            const file = this.files[0];
            content.innerHTML = `
                <span class="drop-icon">✅</span>
                <div class="drop-text">File Selected</div>
                <div class="drop-hint">
                    ${fileUtils.getFileIcon(file.name)} ${file.name}<br>
                    <small style="color: var(--text-secondary);">${fileUtils.formatFileSize(file.size)}</small>
                </div>
                ${this.options.showPreview ? this.createPreview(file) : ''}
            `;
        } else {
            // 显示多个文件
            content.innerHTML = `
                <span class="drop-icon">✅</span>
                <div class="drop-text">${this.files.length} Files Selected</div>
                <div class="drop-hint">
                    ${this.files.map(file => 
                        `${fileUtils.getFileIcon(file.name)} ${file.name} (${fileUtils.formatFileSize(file.size)})`
                    ).join('<br>')}
                </div>
            `;
        }

        // 添加清除按钮（如果有文件）
        if (this.files.length > 0) {
            const clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'clear-files-btn';
            clearBtn.innerHTML = '🗑️ Clear';
            clearBtn.style.cssText = `
                position: absolute;
                top: var(--spacing-sm);
                right: var(--spacing-sm);
                background: var(--color-error);
                color: white;
                border: none;
                border-radius: var(--border-radius-sm);
                padding: var(--spacing-xs) var(--spacing-sm);
                font-size: var(--font-size-xs);
                cursor: pointer;
                transition: var(--transition-fast);
            `;
            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearFiles();
            });
            this.dropZone.appendChild(clearBtn);
        }
    }

    createPreview(file) {
        if (file.type.startsWith('audio/')) {
            return `
                <div style="margin-top: var(--spacing-md); text-align: center;">
                    <audio controls style="max-width: 100%; height: 40px;">
                        <source src="${URL.createObjectURL(file)}" type="${file.type}">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            `;
        } else if (file.type.startsWith('video/')) {
            return `
                <div style="margin-top: var(--spacing-md); text-align: center;">
                    <video controls style="max-width: 100%; max-height: 200px;">
                        <source src="${URL.createObjectURL(file)}" type="${file.type}">
                        Your browser does not support the video element.
                    </video>
                </div>
            `;
        }
        return '';
    }

    clearFiles() {
        this.files = [];
        this.fileInput.value = '';
        this.updateUI();
        this.triggerChangeEvent();
        this.notifications.info('Files cleared');
    }

    createFileList(files) {
        const dataTransfer = new DataTransfer();
        files.forEach(file => dataTransfer.items.add(file));
        return dataTransfer.files;
    }

    triggerChangeEvent() {
        const event = new CustomEvent('filesChanged', {
            detail: {
                files: this.files,
                count: this.files.length,
                totalSize: this.files.reduce((sum, file) => sum + file.size, 0)
            }
        });
        this.dropZone.dispatchEvent(event);
    }

    // 公共方法
    getFiles() {
        return this.files;
    }

    hasFiles() {
        return this.files.length > 0;
    }

    getFileCount() {
        return this.files.length;
    }

    getTotalSize() {
        return this.files.reduce((sum, file) => sum + file.size, 0);
    }

    addFile(file) {
        const validation = this.validateFile(file);
        if (validation.isValid) {
            if (this.options.multipleFiles) {
                this.files.push(file);
            } else {
                this.files = [file];
            }
            this.updateUI();
            this.triggerChangeEvent();
            return true;
        } else {
            this.notifications.error(`Cannot add file: ${validation.error}`);
            return false;
        }
    }

    removeFile(index) {
        if (index >= 0 && index < this.files.length) {
            const removedFile = this.files.splice(index, 1)[0];
            this.updateUI();
            this.triggerChangeEvent();
            this.notifications.info(`Removed: ${removedFile.name}`);
            return true;
        }
        return false;
    }

    reset() {
        this.clearFiles();
    }

    // 事件监听器
    onFilesChanged(callback) {
        this.dropZone.addEventListener('filesChanged', callback);
    }

    offFilesChanged(callback) {
        this.dropZone.removeEventListener('filesChanged', callback);
    }
}

// 全局注册组件
if (typeof window !== 'undefined') {
    window.FileUploadComponent = FileUploadComponent;
}