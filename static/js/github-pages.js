/**
 * Project Bach - GitHub Pages JavaScript
 * 专用于GitHub Pages静态网站的交互功能
 */

import { domUtils, timeUtils } from './shared.js';

/**
 * GitBook 风格导航管理
 */
class GitHubPagesNavigation {
    constructor() {
        this.sidebarOpen = false;
        this.searchActive = false;
        this.scrollObserver = null;
        this.init();
    }

    init() {
        this.setupMobileNavigation();
        this.setupSidebarInteractions();
        this.setupNavigationTree();
        this.setupSearchFunctionality();
        this.setupKeyboardShortcuts();
        this.setupTOC();
    }

    setupMobileNavigation() {
        const toggleButton = document.querySelector('.mobile-menu-toggle');
        const leftSidebar = document.querySelector('.left-sidebar');

        if (toggleButton && leftSidebar) {
            toggleButton.addEventListener('click', () => {
                this.toggleSidebar();
            });

            // 点击内容区域关闭侧边栏
            document.addEventListener('click', (e) => {
                if (this.sidebarOpen && 
                    !leftSidebar.contains(e.target) && 
                    !toggleButton.contains(e.target)) {
                    this.closeSidebar();
                }
            });
        }
    }

    setupNavigationTree() {
        // 设置导航树折叠/展开功能
        const treeToggles = document.querySelectorAll('.nav-tree-toggle');
        
        treeToggles.forEach(toggle => {
            toggle.addEventListener('click', () => {
                const targetId = toggle.dataset.target;
                const submenu = document.getElementById(targetId);
                const expanded = toggle.getAttribute('aria-expanded') === 'true';
                
                if (submenu) {
                    toggle.setAttribute('aria-expanded', !expanded);
                    submenu.classList.toggle('collapsed', expanded);
                    
                    // 更新图标
                    const expandIcon = toggle.querySelector('.nav-expand-icon');
                    if (expandIcon) {
                        expandIcon.textContent = expanded ? '▶' : '▼';
                    }
                }
            });
        });

        // 活动链接高亮
        this.highlightActiveNavItems();
    }

    setupSidebarInteractions() {
        // 活动链接高亮
        const navLinks = document.querySelectorAll('.nav-links a');
        const currentPath = window.location.pathname;

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath || 
                link.getAttribute('href') === currentPath.replace('.html', '')) {
                link.classList.add('active');
            }

            // 悬停效果
            link.addEventListener('mouseenter', () => {
                this.previewContent(link.getAttribute('href'));
            });
        });
    }

    setupContentFiltering() {
        // 内容类型筛选
        const filterButtons = document.querySelectorAll('[data-filter]');
        const contentItems = document.querySelectorAll('.result-item');

        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                const filterType = button.dataset.filter;
                this.filterContent(filterType, contentItems);
                
                // 更新按钮状态
                filterButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
            });
        });
    }

    setupSearchFunctionality() {
        const searchInput = document.querySelector('#nav-search');
        
        if (searchInput) {
            let searchTimeout;
            
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performNavSearch(e.target.value.trim());
                }, 200);
            });

            searchInput.addEventListener('focus', () => {
                this.searchActive = true;
                searchInput.parentElement.classList.add('search-active');
            });

            searchInput.addEventListener('blur', () => {
                this.searchActive = false;
                searchInput.parentElement.classList.remove('search-active');
            });
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Slash key (/) to focus search
            if (e.key === '/' && !this.searchActive) {
                e.preventDefault();
                const searchInput = document.querySelector('#nav-search');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }

            // Escape key to close search or sidebar
            if (e.key === 'Escape') {
                if (this.searchActive) {
                    const searchInput = document.querySelector('#nav-search');
                    if (searchInput) {
                        searchInput.blur();
                        searchInput.value = '';
                        this.clearNavSearch();
                    }
                } else if (this.sidebarOpen) {
                    this.closeSidebar();
                }
            }

            // Command/Ctrl + K for search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('#nav-search');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
        });
    }

    setupTOC() {
        this.generateTOC();
        this.setupTOCInteractions();
    }

    toggleSidebar() {
        const leftSidebar = document.querySelector('.left-sidebar');
        if (leftSidebar) {
            this.sidebarOpen = !this.sidebarOpen;
            leftSidebar.classList.toggle('open', this.sidebarOpen);
            
            // 更新切换按钮图标
            const toggleButton = document.querySelector('.mobile-menu-toggle');
            if (toggleButton) {
                toggleButton.innerHTML = this.sidebarOpen ? '✕' : '☰';
            }
        }
    }

    closeSidebar() {
        const leftSidebar = document.querySelector('.left-sidebar');
        if (leftSidebar && this.sidebarOpen) {
            this.sidebarOpen = false;
            leftSidebar.classList.remove('open');
            
            const toggleButton = document.querySelector('.mobile-menu-toggle');
            if (toggleButton) {
                toggleButton.innerHTML = '☰';
            }
        }
    }

    // ===== TOC 功能 =====
    generateTOC() {
        const tocList = document.querySelector('#toc-list');
        
        // 明确优先查找动态内容，完全忽略静态内容
        let contentBody = document.querySelector('.loaded-content, .markdown-content');
        if (!contentBody) {
            // 只有当没有动态内容时才回退到静态内容
            contentBody = document.querySelector('.content-body, .main-content');
        }
        
        if (!tocList || !contentBody) {
            console.log('TOC: Required elements not found', {tocList: !!tocList, contentBody: !!contentBody});
            return;
        }

        console.log('TOC: Generating TOC for', contentBody.className, contentBody);
        
        // 查找所有标题元素
        const headings = contentBody.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        if (headings.length === 0) {
            this.showEmptyTOC(tocList);
            return;
        }

        // 完全清空TOC，重新生成
        tocList.innerHTML = '';

        headings.forEach((heading, index) => {
            // 为标题添加ID（如果没有的话）
            if (!heading.id) {
                // 检查是否是动态内容区域的标题
                const isDynamicContent = heading.closest('.loaded-content, .markdown-content');
                const prefix = isDynamicContent ? 'dynamic-heading' : 'heading';
                heading.id = `${prefix}-${index + 1}`;
            }

            const level = parseInt(heading.tagName.charAt(1));
            const tocItem = this.createTOCItem(heading, level);
            tocList.appendChild(tocItem);
        });

        this.setupScrollSync();
    }

    createTOCItem(heading, level) {
        const li = document.createElement('li');
        li.className = `toc-item level-${level}`;

        const link = document.createElement('a');
        link.href = `#${heading.id}`;
        link.className = 'toc-link';
        link.textContent = heading.textContent;
        
        // 平滑滚动到目标位置
        link.addEventListener('click', (e) => {
            e.preventDefault();
            this.scrollToHeading(heading);
        });

        li.appendChild(link);
        return li;
    }

    setupTOCInteractions() {
        const tocToggle = document.querySelector('#toc-toggle');
        const tocContent = document.querySelector('#toc-content');

        if (tocToggle && tocContent) {
            tocToggle.addEventListener('click', () => {
                tocContent.classList.toggle('collapsed');
                const collapsed = tocContent.classList.contains('collapsed');
                tocToggle.setAttribute('aria-expanded', !collapsed);
                
                // 更新按钮文本
                const icon = tocToggle.querySelector('.toc-toggle-icon');
                if (icon) {
                    icon.textContent = collapsed ? '📋' : '📑';
                }
            });
        }
    }

    setupScrollSync() {
        // 滚动同步：高亮当前可见的标题
        const tocLinks = document.querySelectorAll('.toc-link');
        
        // 使用与generateTOC相同的逻辑查找内容区域
        let contentBody = document.querySelector('.loaded-content, .markdown-content');
        if (!contentBody) {
            contentBody = document.querySelector('.content-body, .main-content');
        }
        
        const headings = contentBody ? contentBody.querySelectorAll('h1, h2, h3, h4, h5, h6') : document.querySelectorAll('h1, h2, h3, h4, h5, h6');

        if (tocLinks.length === 0 || headings.length === 0) {
            console.log('TOC ScrollSync: No links or headings found', {
                tocLinks: tocLinks.length, 
                headings: headings.length,
                contentBody: !!contentBody
            });
            return;
        }

        // 清除之前的观察器（如果存在）
        if (this.scrollObserver) {
            this.scrollObserver.disconnect();
        }

        // 最简单的滚动高亮逻辑
        this.scrollObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.id;
                    const tocLink = document.querySelector(`.toc-link[href="#${id}"]`);
                    
                    if (tocLink) {
                        // 移除所有活动状态
                        tocLinks.forEach(link => link.classList.remove('active'));
                        // 添加当前活动状态
                        tocLink.classList.add('active');
                    }
                }
            });
        });

        headings.forEach(heading => this.scrollObserver.observe(heading));
    }

    scrollToHeading(heading) {
        heading.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }

    showEmptyTOC(tocList) {
        tocList.innerHTML = '<li class="toc-empty">No headings found in content</li>';
    }

    // ===== 导航搜索功能 =====
    performNavSearch(query) {
        const navItems = document.querySelectorAll('.nav-tree-link, .nav-links a');
        
        if (!query) {
            this.clearNavSearch();
            return;
        }

        const queryLower = query.toLowerCase();
        
        navItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            const matches = text.includes(queryLower);
            
            if (matches) {
                item.style.display = 'flex';
                this.highlightSearchTermInNav(item, query);
                
                // 展开父级菜单
                const parentSubmenu = item.closest('.nav-tree-submenu');
                if (parentSubmenu) {
                    parentSubmenu.classList.remove('collapsed');
                    const parentToggle = document.querySelector(`[data-target="${parentSubmenu.id}"]`);
                    if (parentToggle) {
                        parentToggle.setAttribute('aria-expanded', 'true');
                        const expandIcon = parentToggle.querySelector('.nav-expand-icon');
                        if (expandIcon) expandIcon.textContent = '▼';
                    }
                }
            } else {
                item.style.display = 'none';
            }
        });
    }

    clearNavSearch() {
        const navItems = document.querySelectorAll('.nav-tree-link, .nav-links a');
        
        navItems.forEach(item => {
            item.style.display = '';
            // 清除搜索高亮
            const highlights = item.querySelectorAll('.search-highlight');
            highlights.forEach(highlight => {
                highlight.replaceWith(document.createTextNode(highlight.textContent));
            });
        });
    }

    highlightSearchTermInNav(element, query) {
        // 清除之前的高亮
        const oldHighlights = element.querySelectorAll('.search-highlight');
        oldHighlights.forEach(h => h.replaceWith(document.createTextNode(h.textContent)));
        
        // 添加新的高亮
        const textNodes = this.getTextNodes(element);
        const regex = new RegExp(`(${query})`, 'gi');
        
        textNodes.forEach(node => {
            if (node.textContent.match(regex)) {
                const parent = node.parentNode;
                const fragment = document.createDocumentFragment();
                const parts = node.textContent.split(regex);
                
                for (let i = 0; i < parts.length; i++) {
                    if (i % 2 === 0) {
                        if (parts[i]) fragment.appendChild(document.createTextNode(parts[i]));
                    } else {
                        const mark = document.createElement('mark');
                        mark.className = 'search-highlight';
                        mark.textContent = parts[i];
                        fragment.appendChild(mark);
                    }
                }
                
                parent.replaceChild(fragment, node);
            }
        });
    }

    highlightActiveNavItems() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-tree-link, .nav-links a');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (href === currentPath || href === currentPath.replace('.html', ''))) {
                link.classList.add('active');
                
                // 展开父级菜单
                const parentSubmenu = link.closest('.nav-tree-submenu');
                if (parentSubmenu) {
                    parentSubmenu.classList.remove('collapsed');
                    const parentToggle = document.querySelector(`[data-target="${parentSubmenu.id}"]`);
                    if (parentToggle) {
                        parentToggle.setAttribute('aria-expanded', 'true');
                    }
                }
            }
        });
    }

    previewContent(href) {
        // 简单的内容预览功能
        console.log(`Previewing: ${href}`);
    }

    filterContent(filterType, contentItems) {
        contentItems.forEach(item => {
            if (filterType === 'all' || item.classList.contains(`content-${filterType}`)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });

        // 更新结果计数
        const visibleItems = Array.from(contentItems).filter(item => 
            item.style.display !== 'none').length;
        
        this.updateResultsCount(visibleItems, contentItems.length);
    }

    performSearch(query, resultsContainer) {
        if (!query.trim()) {
            this.clearSearch(resultsContainer);
            return;
        }

        const contentItems = document.querySelectorAll('.result-item');
        const matchedItems = [];

        contentItems.forEach(item => {
            const title = item.querySelector('h3')?.textContent || '';
            const content = item.textContent.toLowerCase();
            const searchQuery = query.toLowerCase();

            if (title.toLowerCase().includes(searchQuery) || 
                content.includes(searchQuery)) {
                matchedItems.push(item);
                item.style.display = 'block';
                this.highlightSearchTerms(item, query);
            } else {
                item.style.display = 'none';
            }
        });

        this.updateSearchResults(matchedItems.length, query, resultsContainer);
    }

    highlightSearchTerms(element, query) {
        // 简单的搜索词高亮
        const textNodes = this.getTextNodes(element);
        const regex = new RegExp(`(${query})`, 'gi');

        textNodes.forEach(node => {
            if (node.textContent.match(regex)) {
                const highlightedText = node.textContent.replace(regex, 
                    '<mark class="search-highlight">$1</mark>');
                const wrapper = document.createElement('span');
                wrapper.innerHTML = highlightedText;
                node.parentNode.replaceChild(wrapper, node);
            }
        });
    }

    getTextNodes(element) {
        const textNodes = [];
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }

        return textNodes;
    }

    clearSearch(resultsContainer) {
        const contentItems = document.querySelectorAll('.result-item');
        contentItems.forEach(item => {
            item.style.display = 'block';
            // 清除高亮
            const highlights = item.querySelectorAll('.search-highlight');
            highlights.forEach(highlight => {
                highlight.outerHTML = highlight.textContent;
            });
        });

        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
    }

    updateResultsCount(visible, total) {
        const countElement = document.querySelector('.results-count');
        if (countElement) {
            countElement.textContent = `Showing ${visible} of ${total} items`;
        }
    }

    updateSearchResults(count, query, container) {
        if (container) {
            container.innerHTML = `
                <div class="search-summary">
                    Found ${count} results for "${query}"
                    ${count === 0 ? '<br><small>Try different keywords or check spelling</small>' : ''}
                </div>
            `;
        }
    }
}

/**
 * GitHub Pages 内容管理
 */
class GitHubPagesContent {
    constructor() {
        this.init();
    }

    init() {
        this.setupLazyLoading();
        this.setupContentExpansion();
        this.setupRelativeTime();
        this.setupContentSharing();
    }

    setupLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for older browsers
            images.forEach(img => {
                img.src = img.dataset.src;
                img.classList.remove('lazy');
            });
        }
    }

    setupContentExpansion() {
        const expandButtons = document.querySelectorAll('.expand-content');
        
        expandButtons.forEach(button => {
            button.addEventListener('click', () => {
                const content = button.nextElementSibling;
                const isExpanded = content.classList.contains('expanded');
                
                content.classList.toggle('expanded');
                button.textContent = isExpanded ? 'Show More' : 'Show Less';
                button.setAttribute('aria-expanded', !isExpanded);
            });
        });
    }

    setupRelativeTime() {
        const timeElements = document.querySelectorAll('[data-timestamp]');
        
        timeElements.forEach(element => {
            const timestamp = element.dataset.timestamp;
            if (timestamp) {
                element.textContent = timeUtils.timeAgo(timestamp);
                element.title = new Date(timestamp).toLocaleString();
            }
        });

        // 每分钟更新相对时间
        setInterval(() => {
            timeElements.forEach(element => {
                const timestamp = element.dataset.timestamp;
                if (timestamp) {
                    element.textContent = timeUtils.timeAgo(timestamp);
                }
            });
        }, 60000);
    }

    setupContentSharing() {
        const shareButtons = document.querySelectorAll('.share-button');
        
        shareButtons.forEach(button => {
            button.addEventListener('click', () => {
                if (navigator.share) {
                    navigator.share({
                        title: document.title,
                        url: window.location.href
                    });
                } else {
                    // Fallback: copy to clipboard
                    navigator.clipboard.writeText(window.location.href).then(() => {
                        this.showShareSuccess(button);
                    });
                }
            });
        });
    }

    showShareSuccess(button) {
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.classList.add('success');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('success');
        }, 2000);
    }
}

/**
 * GitHub Pages 主应用初始化
 */
class GitHubPagesApp {
    constructor() {
        this.navigation = new GitHubPagesNavigation();
        this.content = new GitHubPagesContent();
        this.init();
    }

    init() {
        this.setupServiceWorker();
        this.setupAnalytics();
        this.setupErrorHandling();
        
        console.log('GitHub Pages App initialized');
    }

    setupServiceWorker() {
        // Service Worker功能暂时禁用，避免404错误
        // 如果需要，可以创建/sw.js文件并启用此功能
        if (false && 'serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
                })
                .catch(error => {
                    console.log('SW registration failed:', error);
                });
        }
    }

    setupAnalytics() {
        // 简单的页面访问统计
        if (typeof gtag !== 'undefined') {
            gtag('config', 'GA_TRACKING_ID', {
                page_title: document.title,
                page_location: window.location.href
            });
        }
    }

    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.githubPagesApp = new GitHubPagesApp();
});

// 导出模块
export { GitHubPagesNavigation, GitHubPagesContent, GitHubPagesApp };