/**
 * Dynamic Content Loader
 * 动态内容加载功能 - 支持在侧栏点击内容时动态加载到中间区域
 * 支持直接加载和渲染Markdown文件
 */

class DynamicContentLoader {
    constructor() {
        this.welcomeContent = null;
        this.dynamicContent = null;
        this.initialized = false;
    }

    /**
     * 初始化动态内容加载器
     */
    init() {
        if (this.initialized) return;
        
        this.welcomeContent = document.getElementById('welcome-content');
        this.dynamicContent = document.getElementById('dynamic-content');
        
        if (!this.welcomeContent || !this.dynamicContent) {
            console.warn('Dynamic content loader: Required elements not found');
            return;
        }

        this.bindEvents();
        this.initialized = true;
        console.log('Dynamic content loader initialized');
    }

    /**
     * 绑定事件处理器
     */
    bindEvents() {
        // 绑定内容项点击事件
        document.addEventListener('click', (e) => {
            if (e.target.closest('.content-item-link')) {
                e.preventDefault();
                const link = e.target.closest('.content-item-link');
                const url = link.getAttribute('data-url');
                const title = link.getAttribute('data-title');
                const type = link.getAttribute('data-type');
                
                this.loadContent(url, title, type);
            }
            
            // 绑定面包屑点击事件
            if (e.target.closest('.breadcrumb-item')) {
                e.preventDefault();
                const breadcrumbItem = e.target.closest('.breadcrumb-item');
                this.handleBreadcrumbClick(breadcrumbItem);
            }
        });

        // 绑定搜索功能
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('content-search');
        
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.performSearch());
        }
        
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch();
                }
            });
        }

        // 绑定全局返回Hub功能
        window.showWelcome = () => this.showWelcome();
    }

    /**
     * 生成面包屑导航HTML
     * @param {string} title - 内容标题
     */
    generateBreadcrumb(title) {
        const breadcrumbParts = [];
        
        // 动态查找当前激活项的层级结构
        const activeLink = document.querySelector('.content-item-link.active') || 
                          document.querySelector('.nav-tree-link.active');
        
        if (activeLink) {
            // 向上遍历DOM树，收集层级信息
            let current = activeLink;
            const hierarchy = [];
            
            while (current) {
                // 查找父级菜单项
                const parentSubmenu = current.closest('.nav-tree-submenu');
                if (parentSubmenu) {
                    const toggleButton = document.querySelector(`[data-target="${parentSubmenu.id}"]`);
                    if (toggleButton) {
                        const label = toggleButton.querySelector('.nav-tree-label')?.textContent?.trim();
                        if (label && !hierarchy.includes(label)) {
                            hierarchy.unshift(label); // 添加到开头，保持正确顺序
                        }
                    }
                    current = parentSubmenu.parentNode;
                } else {
                    break;
                }
            }
            
            // 添加收集到的层级
            breadcrumbParts.push(...hierarchy);
        }
        
        // 添加内容标题
        breadcrumbParts.push(title);
        
        // 生成HTML，中间项设为可点击
        return breadcrumbParts.map((part, index) => {
            if (index === breadcrumbParts.length - 1) {
                // 最后一项，当前页面，不可点击
                return `<span class="breadcrumb-current">${this.escapeHtml(part)}</span>`;
            } else {
                // 中间项，可点击
                return `<span class="breadcrumb-item" data-breadcrumb-level="${index}" data-breadcrumb-text="${this.escapeHtml(part)}">${this.escapeHtml(part)}</span>`;
            }
        }).join(' <span class="breadcrumb-separator">/</span> ').trim();
    }

    /**
     * 处理面包屑点击事件
     * @param {Element} breadcrumbItem - 被点击的面包屑项
     */
    handleBreadcrumbClick(breadcrumbItem) {
        const level = parseInt(breadcrumbItem.getAttribute('data-breadcrumb-level'));
        const text = breadcrumbItem.getAttribute('data-breadcrumb-text');
        
        console.log(`Breadcrumb clicked: Level ${level}, Text: ${text}`);
        
        // 根据层级执行不同的操作
        if (level === 0) {
            // 点击了顶级分类（如 Lectures, Videos）
            this.showWelcome(); // 返回欢迎页面，展示该分类
        } else if (level === 1) {
            // 点击了子分类（如 CS101, PHYS101）  
            // 可以展开该分类但不加载具体内容
            this.expandCategoryInNavigation(text);
        }
        // level === 2 是当前页面，不需要处理
    }

    /**
     * 在导航树中展开指定分类
     * @param {string} categoryName - 分类名称
     */
    expandCategoryInNavigation(categoryName) {
        // 找到对应的toggle按钮并展开
        const toggles = document.querySelectorAll('.nav-tree-toggle');
        
        toggles.forEach(toggle => {
            const label = toggle.querySelector('.nav-tree-label');
            if (label && label.textContent.trim() === categoryName) {
                // 找到了，确保展开
                const targetId = toggle.getAttribute('data-target');
                const submenu = document.getElementById(targetId);
                
                if (submenu && submenu.classList.contains('collapsed')) {
                    // 如果是折叠状态，则展开
                    toggle.setAttribute('aria-expanded', 'true');
                    submenu.classList.remove('collapsed');
                    
                    const expandIcon = toggle.querySelector('.nav-expand-icon');
                    if (expandIcon) {
                        expandIcon.textContent = '⌄';
                    }
                }
                
                // 高亮该按钮
                toggle.classList.add('active');
                setTimeout(() => toggle.classList.remove('active'), 1000);
            }
        });
        
        // 返回到欢迎页面
        this.showWelcome();
    }

    /**
     * 加载指定URL的内容
     * @param {string} url - 内容URL
     * @param {string} title - 内容标题
     * @param {string} type - 内容类型
     */
    loadContent(url, title, type) {
        if (!this.welcomeContent || !this.dynamicContent) return;

        // 更新活动状态
        this.updateActiveState(url);
        
        // 隐藏欢迎内容，显示动态内容区域
        this.welcomeContent.classList.remove('active');
        this.welcomeContent.style.display = 'none';
        this.dynamicContent.classList.remove('hidden');
        this.dynamicContent.style.display = 'block';
        
        // 显示加载状态
        this.dynamicContent.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Loading ${title}...</p>
            </div>
        `;
        
        // 将HTML URL转换为Markdown URL
        const markdownUrl = url.replace('_result.html', '_result.md');
        
        // 通过AJAX加载Markdown内容
        fetch(markdownUrl)
            .then(response => {
                if (!response.ok) {
                    // 如果Markdown文件不存在，回退到HTML加载
                    return fetch(url).then(htmlResponse => {
                        if (!htmlResponse.ok) {
                            throw new Error(`HTTP ${htmlResponse.status}: ${htmlResponse.statusText}`);
                        }
                        return { content: htmlResponse.text(), type: 'html' };
                    });
                }
                return { content: response.text(), type: 'markdown' };
            })
            .then(async result => {
                const content = await result.content;
                if (result.type === 'markdown') {
                    this.renderMarkdownContent(content, title, type, markdownUrl);
                } else {
                    this.renderLoadedContent(content, title, type, url);
                }
            })
            .catch(error => this.renderErrorContent(error, title, url));
    }

    /**
     * 渲染Markdown内容
     * @param {string} markdown - Markdown内容
     * @param {string} title - 内容标题
     * @param {string} type - 内容类型
     * @param {string} url - 原始URL
     */
    renderMarkdownContent(markdown, title, type, url) {
        // 简单的Markdown到HTML转换
        const html = this.parseMarkdown(markdown);
        
        const breadcrumbHtml = this.generateBreadcrumb(title);
        
        this.dynamicContent.innerHTML = `
            <div class="content-header">
                <div class="content-breadcrumb">
                    ${breadcrumbHtml}
                </div>
                <div class="content-title-area">
                    <h1>${this.escapeHtml(title)}</h1>
                    <span class="content-type-badge badge-${type}">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                </div>
            </div>
            <div class="loaded-content markdown-content">
                ${html}
            </div>
        `;
        
        // 重新生成TOC
        this.updateTOC();
    }

    /**
     * 使用marked.js的专业Markdown解析器
     * @param {string} markdown - Markdown文本
     * @returns {string} HTML文本
     */
    parseMarkdown(markdown) {
        // 确保marked库已加载
        if (typeof marked === 'undefined') {
            console.error('marked.js library not loaded, falling back to basic parsing');
            return this.basicMarkdownParse(markdown);
        }
        
        // 配置marked选项
        marked.setOptions({
            // 启用GitHub风格Markdown
            gfm: true,
            // 启用表格
            tables: true,
            // 启用换行符转换
            breaks: false,
            // 启用删除线
            strikethrough: true,
            // 启用任务列表
            tasklists: true,
            // 安全设置：过滤HTML
            sanitize: false, // 我们手动处理
            // 代码高亮准备
            highlight: null,
            // 链接在新窗口打开
            renderer: this.getCustomRenderer()
        });
        
        try {
            // 预处理：清理不需要的内容
            let cleanMarkdown = this.preprocessMarkdown(markdown);
            
            // 使用marked进行转换
            let html = marked.parse(cleanMarkdown);
            
            // 后处理：应用自定义样式和清理
            html = this.postprocessHTML(html);
            
            return html;
        } catch (error) {
            console.error('Markdown parsing error:', error);
            return this.basicMarkdownParse(markdown);
        }
    }
    
    /**
     * 获取自定义的marked渲染器
     * @returns {Object} marked渲染器
     */
    getCustomRenderer() {
        const renderer = new marked.Renderer();
        
        // 自定义链接渲染：在新窗口打开外部链接
        renderer.link = function(href, title, text) {
            const isExternal = href && (href.startsWith('http') || href.startsWith('//'));
            const target = isExternal ? ' target="_blank" rel="noopener noreferrer"' : '';
            const titleAttr = title ? ` title="${title}"` : '';
            return `<a href="${href}"${titleAttr}${target}>${text}</a>`;
        };
        
        // 自定义表格渲染：添加CSS类
        renderer.table = function(header, body) {
            return `<table class="markdown-table">
                <thead>${header}</thead>
                <tbody>${body}</tbody>
            </table>`;
        };
        
        // 自定义代码块渲染：添加语言标识
        renderer.code = function(code, language, escaped) {
            // Debug logging
            console.log('Code renderer called with:', {
                code: typeof code === 'object' ? 'object' : code, 
                language, 
                escaped,
                codeText: typeof code === 'object' ? code.text : code
            });
            
            // Extract actual code text from marked.js token object or use as string
            let codeText = '';
            if (typeof code === 'object' && code !== null) {
                codeText = code.text || code.raw || String(code);
            } else {
                codeText = String(code || '');
            }
            
            const langClass = language ? ` class="language-${language}"` : '';
            const langLabel = language ? `<span class="code-lang">${language}</span>` : '';
            
            // HTML转义（如果marked.js没有处理过）
            const escapedCode = escaped ? codeText : codeText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            
            const result = `<div class="code-block">
                ${langLabel}
                <pre><code${langClass}>${escapedCode}</code></pre>
            </div>`;
            
            console.log('Code renderer returning first 100 chars:', result.substring(0, 100));
            return result;
        };
        
        return renderer;
    }
    
    /**
     * 预处理Markdown内容
     * @param {string} markdown - 原始Markdown
     * @returns {string} 清理后的Markdown
     */
    preprocessMarkdown(markdown) {
        let cleaned = markdown;
        
        // 移除HTML标签（保留marked.js处理）
        cleaned = cleaned.replace(/<title>.*?<\/title>/gi, '');
        cleaned = cleaned.replace(/^\s*<[^>]+>\s*/gm, '');
        
        // 移除开头的分隔线
        cleaned = cleaned.replace(/^---+\s*\n/m, '');
        
        // 清理开头空白
        cleaned = cleaned.trim();
        
        return cleaned;
    }
    
    /**
     * 后处理HTML内容
     * @param {string} html - marked生成的HTML
     * @returns {string} 最终HTML
     */
    postprocessHTML(html) {
        let processed = html;
        
        // 移除空的段落
        processed = processed.replace(/<p>\s*<\/p>/g, '');
        
        // 确保表格有正确的CSS类（双重保险）
        processed = processed.replace(/<table>/g, '<table class="markdown-table">');
        
        return processed;
    }
    
    /**
     * 基础Markdown解析器（fallback）
     * @param {string} markdown - Markdown文本
     * @returns {string} HTML文本
     */
    basicMarkdownParse(markdown) {
        let html = markdown;
        
        // 基础标题处理
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        
        // 基础格式处理
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // 段落处理
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        html = html.replace(/<p><\/p>/g, '');
        
        return html;
    }

    /**
     * 渲染成功加载的内容
     * @param {string} html - 加载的HTML内容
     * @param {string} title - 内容标题
     * @param {string} type - 内容类型
     * @param {string} url - 原始URL
     */
    renderLoadedContent(html, title, type, url) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 尝试多个选择器来提取主要内容
        const contentSelectors = [
            '.content-section',
            'main article',
            'main .main-content',
            '.section',
            'main',
            'article'
        ];
        
        let mainContent = null;
        for (const selector of contentSelectors) {
            mainContent = doc.querySelector(selector);
            if (mainContent) break;
        }
        
        if (mainContent) {
            const breadcrumbHtml = this.generateBreadcrumb(title);
            
            this.dynamicContent.innerHTML = `
                <div class="content-header">
                    <div class="content-breadcrumb">
                        ${breadcrumbHtml}
                    </div>
                    <div class="content-title-area">
                        <h1>${this.escapeHtml(title)}</h1>
                        <span class="content-type-badge badge-${type}">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                    </div>
                </div>
                <div class="loaded-content">
                    ${mainContent.innerHTML}
                </div>
            `;
        } else {
            this.renderErrorContent(new Error('Could not parse content'), title, url);
        }
    }

    /**
     * 渲染错误内容
     * @param {Error} error - 错误对象
     * @param {string} title - 内容标题
     * @param {string} url - 原始URL
     */
    renderErrorContent(error, title, url) {
        console.error('Content loading error:', error);
        
        this.dynamicContent.innerHTML = `
            <div class="content-header">
                <div class="content-title-area">
                    <h1>${this.escapeHtml(title)}</h1>
                </div>
            </div>
            <div class="error-message">
                <div class="error-icon">⚠️</div>
                <p>Could not load content</p>
                <p class="error-detail">${this.escapeHtml(error.message)}</p>
                <a href="${url}" target="_blank" class="btn btn-primary">
                    📄 Open in new tab
                </a>
            </div>
        `;
    }

    /**
     * 显示欢迎页面
     */
    showWelcome() {
        if (!this.welcomeContent || !this.dynamicContent) return;
        
        // 清除活动状态
        this.clearActiveStates();
        
        // 显示欢迎内容，隐藏动态内容
        this.welcomeContent.classList.add('active');
        this.welcomeContent.style.display = 'block';
        this.dynamicContent.classList.add('hidden');
        this.dynamicContent.style.display = 'none';
        
        // 完全清空动态内容，移除所有动态内容类
        this.dynamicContent.innerHTML = '';
        this.dynamicContent.classList.remove('loaded-content', 'markdown-content');
        
        // 重新生成TOC，这次会显示静态内容的TOC
        this.updateTOC();
    }

    /**
     * 执行搜索功能
     */
    performSearch() {
        const searchQuery = document.getElementById('content-search')?.value;
        const category = document.getElementById('search-category')?.value;
        
        if (!searchQuery || !searchQuery.trim()) {
            alert('Please enter a search term');
            return;
        }
        
        // 显示搜索结果 (这里可以扩展为更复杂的搜索功能)
        console.log('Searching for:', searchQuery, 'in category:', category);
        
        // TODO: 实现实际的搜索功能
        // 可以调用后端API或执行客户端搜索
        alert(`Searching for "${searchQuery}" in ${category || 'all categories'}.\nSearch functionality coming soon!`);
    }

    /**
     * 更新活动状态
     * @param {string} activeUrl - 当前活动的URL
     */
    updateActiveState(activeUrl) {
        // 清除所有活动状态
        this.clearActiveStates();
        
        // 设置新的活动状态
        const activeLink = document.querySelector(`[data-url="${activeUrl}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    /**
     * 清除所有活动状态
     */
    clearActiveStates() {
        document.querySelectorAll('.content-item-link.active').forEach(link => {
            link.classList.remove('active');
        });
    }

    /**
     * 更新右侧TOC
     */
    updateTOC() {
        // 调用GitHub Pages app的TOC生成功能
        if (window.githubPagesApp && window.githubPagesApp.navigation && 
            window.githubPagesApp.navigation.generateTOC) {
            window.githubPagesApp.navigation.generateTOC();
        } else {
            console.warn('GitHub Pages TOC system not available');
        }
    }


    /**
     * HTML转义
     * @param {string} text - 需要转义的文本
     * @returns {string} 转义后的文本
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 创建全局实例
const dynamicContentLoader = new DynamicContentLoader();

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    dynamicContentLoader.init();
});

// 导出给其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicContentLoader;
}