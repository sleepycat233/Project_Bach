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
        
        this.dynamicContent.innerHTML = `
            <div class="content-header">
                <button class="back-btn btn btn-secondary" onclick="showWelcome()">
                    <span>← Back to Hub</span>
                </button>
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
     * 简单的Markdown解析器
     * @param {string} markdown - Markdown文本
     * @returns {string} HTML文本
     */
    parseMarkdown(markdown) {
        let html = markdown;
        
        // 处理标题
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
        html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
        
        // 处理加粗和斜体
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // 处理代码块
        html = html.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 处理链接
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        
        // 处理列表
        html = html.replace(/^[-*+] (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // 处理表格
        html = html.replace(/\|(.+)\|/g, (match, content) => {
            const cells = content.split('|').map(cell => cell.trim());
            return '<tr>' + cells.map(cell => `<td>${cell}</td>`).join('') + '</tr>';
        });
        html = html.replace(/(<tr>.*<\/tr>)/s, '<table class="markdown-table">$1</table>');
        
        // 处理分隔线
        html = html.replace(/^---+$/gm, '<hr>');
        
        // 处理换行和段落
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        html = html.replace(/<p><\/p>/g, '');
        html = html.replace(/<p>(<h[1-6]>)/g, '$1');
        html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
        html = html.replace(/<p>(<ul>)/g, '$1');
        html = html.replace(/(<\/ul>)<\/p>/g, '$1');
        html = html.replace(/<p>(<pre>)/g, '$1');
        html = html.replace(/(<\/pre>)<\/p>/g, '$1');
        html = html.replace(/<p>(<table)/g, '$1');
        html = html.replace(/(<\/table>)<\/p>/g, '$1');
        html = html.replace(/<p>(<hr>)/g, '$1');
        html = html.replace(/(<hr>)<\/p>/g, '$1');
        
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
            this.dynamicContent.innerHTML = `
                <div class="content-header">
                    <button class="back-btn btn btn-secondary" onclick="showWelcome()">
                        <span>← Back to Hub</span>
                    </button>
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
                <button class="back-btn btn btn-secondary" onclick="showWelcome()">
                    <span>← Back to Hub</span>
                </button>
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