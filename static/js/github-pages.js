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
        this.setupSidebarToggleControls();
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

    setupSidebarToggleControls() {
        // 桌面端侧边栏切换按钮控制
        const leftToggle = document.querySelector('.left-toggle');
        const rightToggle = document.querySelector('.right-toggle');
        const container = document.querySelector('.gitbook-container');
        const leftSidebar = document.querySelector('.left-sidebar');
        const rightSidebar = document.querySelector('.right-sidebar');

        if (leftToggle && container && leftSidebar) {
            leftToggle.addEventListener('click', () => {
                const isHidden = leftSidebar.classList.contains('hidden');
                
                if (isHidden) {
                    // 显示左侧栏
                    leftSidebar.classList.remove('hidden');
                    container.classList.remove('left-hidden', 'both-hidden');
                    leftToggle.classList.remove('active');
                } else {
                    // 隐藏左侧栏
                    leftSidebar.classList.add('hidden');
                    if (rightSidebar && rightSidebar.classList.contains('hidden')) {
                        container.classList.add('both-hidden');
                        container.classList.remove('left-hidden');
                    } else {
                        container.classList.add('left-hidden');
                        container.classList.remove('both-hidden');
                    }
                    leftToggle.classList.add('active');
                }
            });
        }

        if (rightToggle && container && rightSidebar) {
            rightToggle.addEventListener('click', () => {
                const isHidden = rightSidebar.classList.contains('hidden');
                
                if (isHidden) {
                    // 显示右侧栏
                    rightSidebar.classList.remove('hidden');
                    container.classList.remove('right-hidden', 'both-hidden');
                    rightToggle.classList.remove('active');
                } else {
                    // 隐藏右侧栏
                    rightSidebar.classList.add('hidden');
                    if (leftSidebar && leftSidebar.classList.contains('hidden')) {
                        container.classList.add('both-hidden');
                        container.classList.remove('right-hidden');
                    } else {
                        container.classList.add('right-hidden');
                        container.classList.remove('both-hidden');
                    }
                    rightToggle.classList.add('active');
                }
            });
        }
    }

    setupNavigationTree() {
        const nav = document.querySelector('.sidebar-nav, nav');
        if (!nav) return;

        // 核心函数：根据指定的链接元素，更新整个树的状态
        const setTreeState = (targetElement) => {
            if (!targetElement) return;

            // 如果是toggle按钮，获取其父级li
            const targetItem = targetElement.closest('.nav-tree-item');
            if (!targetItem) return;

            // 1. 清除所有active和is-active-path状态（但保留is-open状态用于折叠控制）
            nav.querySelectorAll('.active, .is-active-path').forEach(el => {
                el.classList.remove('active', 'is-active-path');
            });

            // 2. 设置新的激活项
            targetItem.classList.add('active');

            // 3. 沿着路径向上，设置父级的is-active-path状态
            let current = targetItem.parentElement;
            while (current && current !== nav) {
                if (current.classList.contains('nav-tree-submenu')) {
                    current.classList.add('is-active-path');
                }
                const parentItem = current.closest('.nav-tree-item');
                if (parentItem) {
                    parentItem.classList.add('is-active-path');
                }
                current = current.parentElement;
            }
        };

        // 事件委托：处理所有在导航树内的点击
        nav.addEventListener('click', (event) => {
            const toggle = event.target.closest('.nav-tree-toggle');
            
            if (toggle) {
                event.preventDefault();
                const parentLi = toggle.closest('.nav-tree-item');
                const targetId = toggle.dataset.target;
                const submenu = document.getElementById(targetId);
                
                if (parentLi && submenu) {
                    const isOpen = parentLi.classList.contains('is-open');
                    
                    // 手风琴效果：关闭同级的其他菜单
                    const parentContainer = parentLi.parentElement;
                    if (parentContainer && !isOpen) {
                        // 只在打开时关闭其他菜单
                        parentContainer.querySelectorAll(':scope > .nav-tree-item.is-open').forEach(sibling => {
                            if (sibling !== parentLi) {
                                sibling.classList.remove('is-open');
                                const siblingToggle = sibling.querySelector(':scope > .nav-tree-toggle');
                                if (siblingToggle) {
                                    siblingToggle.setAttribute('aria-expanded', 'false');
                                }
                            }
                        });
                    }
                    
                    // 切换当前菜单的折叠状态
                    parentLi.classList.toggle('is-open');
                    toggle.setAttribute('aria-expanded', !isOpen);
                    
                    // 设置为当前激活项
                    setTreeState(toggle);
                }
            } else {
                // 处理链接点击
                const link = event.target.closest('.nav-tree-link');
                if (link) {
                    // 对于所有链接（包括content-item-link），设置高亮状态
                    setTreeState(link);
                }
            }
        });

        // 初始化：展开包含活动链接的所有父级
        this.highlightActiveNavItems();
        
        // 确保初始状态正确
        this.initializeNavigationState();
    }

    initializeNavigationState() {
        // 初始化导航树状态，确保展开包含活动链接的分支
        const activeLink = document.querySelector('.nav-tree-link.active, .nav-tree-link.current');
        if (activeLink) {
            let parent = activeLink.closest('.nav-tree-item');
            while (parent) {
                // 向上遍历，展开所有父级
                const parentItem = parent.parentElement.closest('.nav-tree-item');
                if (parentItem) {
                    parentItem.classList.add('is-open', 'is-active-path');
                    const toggle = parentItem.querySelector(':scope > .nav-tree-toggle');
                    if (toggle) {
                        toggle.setAttribute('aria-expanded', 'true');
                    }
                }
                parent = parentItem;
            }
        }

        // 同步所有is-open状态到aria-expanded
        document.querySelectorAll('.nav-tree-item.is-open').forEach(item => {
            const toggle = item.querySelector(':scope > .nav-tree-toggle');
            if (toggle) {
                toggle.setAttribute('aria-expanded', 'true');
            }
        });
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

        // 延迟设置滚动同步，确保DOM完全渲染
        setTimeout(() => {
            this.setupScrollSync();
        }, 100);
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

        // 清除之前的滚动监听器
        if (this.scrollHandler) {
            window.removeEventListener('scroll', this.scrollHandler);
        }

        // 收集标题信息
        this.headingData = Array.from(headings).map(heading => ({
            element: heading,
            id: heading.id,
            offsetTop: heading.offsetTop
        }));

        this.tocItems = Array.from(tocLinks);
        this.currentActiveIndex = -1;

        // 创建优化的滚动处理器
        let ticking = false;
        this.scrollHandler = () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    this.updateActiveHeading();
                    ticking = false;
                });
                ticking = true;
            }
        };

        // 监听滚动事件
        window.addEventListener('scroll', this.scrollHandler);

        // 监听窗口大小变化，更新偏移位置
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
        }
        this.resizeHandler = () => {
            this.updateHeadingOffsets();
        };
        window.addEventListener('resize', this.resizeHandler);

        // 初始更新
        this.updateActiveHeading();
    }

    updateHeadingOffsets() {
        // 更新所有标题的偏移位置
        if (this.headingData) {
            this.headingData.forEach(heading => {
                heading.offsetTop = heading.element.offsetTop;
            });
        }
    }

    updateActiveHeading() {
        if (!this.headingData || !this.tocItems) return;

        const scrollPosition = window.scrollY + 100; // 添加偏移量以提前触发
        
        // 从后向前遍历，找到第一个offsetTop小于滚动位置的标题
        let activeIndex = -1;
        for (let i = this.headingData.length - 1; i >= 0; i--) {
            if (scrollPosition >= this.headingData[i].offsetTop) {
                activeIndex = i;
                break;
            }
        }

        // 如果激活项发生变化，更新样式
        if (activeIndex !== this.currentActiveIndex) {
            // 移除之前的激活状态
            this.tocItems.forEach(item => {
                item.classList.remove('active');
                // 也移除父级li的active类（如果存在）
                const parentLi = item.closest('.toc-item');
                if (parentLi) {
                    parentLi.classList.remove('active');
                }
            });

            // 添加新的激活状态
            if (activeIndex >= 0 && activeIndex < this.tocItems.length) {
                const activeLink = this.tocItems[activeIndex];
                activeLink.classList.add('active');
                
                // 也为父级li添加active类
                const parentLi = activeLink.closest('.toc-item');
                if (parentLi) {
                    parentLi.classList.add('active');
                }

                // 确保激活项在TOC容器中可见
                this.ensureTOCItemVisible(activeLink);
            }

            this.currentActiveIndex = activeIndex;
        }
    }

    ensureTOCItemVisible(element) {
        const tocContainer = element.closest('.toc, .toc-content');
        if (!tocContainer) return;

        const containerRect = tocContainer.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();

        // 如果元素不在容器可见区域内，滚动使其可见
        if (elementRect.top < containerRect.top || 
            elementRect.bottom > containerRect.bottom) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }

    scrollToHeading(heading) {
        // 计算目标位置，考虑固定header的高度
        const offset = 20; // 顶部偏移量
        const elementPosition = heading.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - offset;

        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
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
                const parentItem = item.closest('.nav-tree-item');
                if (parentItem) {
                    let parent = parentItem.parentElement.closest('.nav-tree-item');
                    while (parent) {
                        parent.classList.add('is-open');
                        const toggle = parent.querySelector(':scope > .nav-tree-toggle');
                        if (toggle) {
                            toggle.setAttribute('aria-expanded', 'true');
                        }
                        parent = parent.parentElement.closest('.nav-tree-item');
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
                // 使用新的active类在nav-tree-item上
                const navItem = link.closest('.nav-tree-item');
                if (navItem) {
                    navItem.classList.add('active');
                    
                    // 展开所有父级菜单并添加is-active-path类
                    let parent = navItem.parentElement.closest('.nav-tree-item');
                    while (parent) {
                        parent.classList.add('is-open', 'is-active-path');
                        const toggle = parent.querySelector(':scope > .nav-tree-toggle');
                        if (toggle) {
                            toggle.setAttribute('aria-expanded', 'true');
                        }
                        parent = parent.parentElement.closest('.nav-tree-item');
                    }
                    
                    // 标记所有父级submenu为active path
                    let submenu = navItem.parentElement.closest('.nav-tree-submenu');
                    while (submenu) {
                        submenu.classList.add('is-active-path');
                        submenu = submenu.parentElement.closest('.nav-tree-submenu');
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