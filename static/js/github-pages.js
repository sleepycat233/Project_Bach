/**
 * Project Bach - GitHub Pages JavaScript
 * 专用于GitHub Pages静态网站的交互功能
 */

import { domUtils, timeUtils } from './shared.js';

/**
 * GitHub Pages 网站导航管理
 */
class GitHubPagesNavigation {
    constructor() {
        this.sidebarOpen = false;
        this.init();
    }

    init() {
        this.setupMobileNavigation();
        this.setupSidebarInteractions();
        this.setupContentFiltering();
        this.setupSearchFunctionality();
    }

    setupMobileNavigation() {
        const toggleButton = document.querySelector('.mobile-menu-toggle');
        const sidebar = document.querySelector('.sidebar');

        if (toggleButton && sidebar) {
            toggleButton.addEventListener('click', () => {
                this.toggleSidebar();
            });

            // 点击内容区域关闭侧边栏
            document.addEventListener('click', (e) => {
                if (this.sidebarOpen && 
                    !sidebar.contains(e.target) && 
                    !toggleButton.contains(e.target)) {
                    this.closeSidebar();
                }
            });

            // ESC键关闭侧边栏
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.sidebarOpen) {
                    this.closeSidebar();
                }
            });
        }
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
        const searchInput = document.querySelector('#search-input');
        const searchResults = document.querySelector('#search-results');

        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performSearch(e.target.value, searchResults);
                }, 300);
            });
        }
    }

    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            this.sidebarOpen = !this.sidebarOpen;
            sidebar.classList.toggle('open', this.sidebarOpen);
            
            // 更新切换按钮图标
            const toggleButton = document.querySelector('.mobile-menu-toggle');
            if (toggleButton) {
                toggleButton.innerHTML = this.sidebarOpen ? '✕' : '☰';
            }
        }
    }

    closeSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && this.sidebarOpen) {
            this.sidebarOpen = false;
            sidebar.classList.remove('open');
            
            const toggleButton = document.querySelector('.mobile-menu-toggle');
            if (toggleButton) {
                toggleButton.innerHTML = '☰';
            }
        }
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
        if ('serviceWorker' in navigator) {
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