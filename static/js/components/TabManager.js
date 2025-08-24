/**
 * TabManager - 标签页管理组件
 * 处理多标签页切换和状态管理功能
 */

export class TabManager {
    constructor(options = {}) {
        this.options = {
            tabButtonsSelector: '.tab-button',
            tabContentsSelector: '.tab-content',
            activeClass: 'active',
            defaultTab: null,
            onTabChange: null,
            localStorage: true,
            storageKey: 'projectbach_active_tab',
            ...options
        };

        this.currentTab = null;
        this.tabs = new Map();
        this.history = [];

        this.init();
    }

    init() {
        this.collectTabs();
        this.setupEventListeners();
        this.initializeDefaultTab();
    }

    collectTabs() {
        const buttons = document.querySelectorAll(this.options.tabButtonsSelector);
        const contents = document.querySelectorAll(this.options.tabContentsSelector);

        buttons.forEach(button => {
            const tabName = button.dataset.tab || button.getAttribute('onclick')?.match(/switchTab\('([^']+)'\)/)?.[1];
            if (tabName) {
                const content = document.getElementById(`${tabName}-tab`) || 
                              Array.from(contents).find(c => c.id.includes(tabName));
                
                if (content) {
                    this.tabs.set(tabName, {
                        name: tabName,
                        button,
                        content,
                        title: button.textContent.trim(),
                        disabled: button.disabled || button.classList.contains('disabled'),
                        visible: !button.classList.contains('hidden')
                    });
                }
            }
        });

        console.log(`TabManager: Found ${this.tabs.size} tabs`, Array.from(this.tabs.keys()));
    }

    setupEventListeners() {
        this.tabs.forEach((tab, tabName) => {
            tab.button.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(tabName);
            });
        });

        // 键盘导航支持
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                const tabNames = Array.from(this.tabs.keys());
                const currentIndex = tabNames.indexOf(this.currentTab);
                
                if (e.key === 'ArrowLeft' && currentIndex > 0) {
                    e.preventDefault();
                    this.switchTab(tabNames[currentIndex - 1]);
                } else if (e.key === 'ArrowRight' && currentIndex < tabNames.length - 1) {
                    e.preventDefault();
                    this.switchTab(tabNames[currentIndex + 1]);
                }
            }
        });

        // 浏览器前进后退支持
        window.addEventListener('popstate', (e) => {
            if (e.state?.tab) {
                this.switchTab(e.state.tab, false);
            }
        });
    }

    initializeDefaultTab() {
        let initialTab = null;

        // 1. 从localStorage恢复
        if (this.options.localStorage) {
            const savedTab = localStorage.getItem(this.options.storageKey);
            if (savedTab && this.tabs.has(savedTab)) {
                initialTab = savedTab;
            }
        }

        // 2. 使用URL hash
        if (!initialTab) {
            const hash = window.location.hash.slice(1);
            if (hash && this.tabs.has(hash)) {
                initialTab = hash;
            }
        }

        // 3. 使用配置的默认标签
        if (!initialTab && this.options.defaultTab && this.tabs.has(this.options.defaultTab)) {
            initialTab = this.options.defaultTab;
        }

        // 4. 使用第一个可用标签
        if (!initialTab) {
            for (const [tabName, tab] of this.tabs) {
                if (!tab.disabled && tab.visible) {
                    initialTab = tabName;
                    break;
                }
            }
        }

        if (initialTab) {
            this.switchTab(initialTab, false);
        }
    }

    switchTab(tabName, updateHistory = true) {
        const tab = this.tabs.get(tabName);
        if (!tab || tab.disabled || !tab.visible) {
            console.warn(`TabManager: Cannot switch to tab "${tabName}"`);
            return false;
        }

        // 如果已经是当前标签，不做任何操作
        if (this.currentTab === tabName) {
            return true;
        }

        const previousTab = this.currentTab;
        
        // 隐藏所有标签内容
        this.tabs.forEach(t => {
            t.content.classList.remove(this.options.activeClass);
            t.button.classList.remove(this.options.activeClass);
        });

        // 显示选中的标签
        tab.content.classList.add(this.options.activeClass);
        tab.button.classList.add(this.options.activeClass);

        this.currentTab = tabName;

        // 更新历史记录
        if (updateHistory) {
            if (previousTab) {
                this.history.push(previousTab);
            }
            
            // 限制历史记录长度
            if (this.history.length > 10) {
                this.history.shift();
            }

            // 更新浏览器历史
            const state = { tab: tabName };
            const url = new URL(window.location);
            url.hash = tabName;
            history.pushState(state, '', url);
        }

        // 保存到localStorage
        if (this.options.localStorage) {
            localStorage.setItem(this.options.storageKey, tabName);
        }

        // 触发标签变化事件
        this.triggerTabChangeEvent(tabName, previousTab);

        // 执行回调
        if (typeof this.options.onTabChange === 'function') {
            this.options.onTabChange(tabName, previousTab, tab);
        }

        console.log(`TabManager: Switched from "${previousTab}" to "${tabName}"`);
        return true;
    }

    triggerTabChangeEvent(newTab, previousTab) {
        const event = new CustomEvent('tabChanged', {
            detail: {
                newTab,
                previousTab,
                tabData: this.tabs.get(newTab)
            }
        });
        document.dispatchEvent(event);
    }

    // 公共方法
    getCurrentTab() {
        return this.currentTab;
    }

    getPreviousTab() {
        return this.history[this.history.length - 1] || null;
    }

    getTabData(tabName) {
        return this.tabs.get(tabName);
    }

    getAllTabs() {
        return Array.from(this.tabs.values());
    }

    getVisibleTabs() {
        return Array.from(this.tabs.values()).filter(tab => tab.visible && !tab.disabled);
    }

    goBack() {
        const previousTab = this.history.pop();
        if (previousTab && this.tabs.has(previousTab)) {
            this.switchTab(previousTab);
            return true;
        }
        return false;
    }

    enableTab(tabName) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            tab.disabled = false;
            tab.button.disabled = false;
            tab.button.classList.remove('disabled');
            return true;
        }
        return false;
    }

    disableTab(tabName) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            tab.disabled = true;
            tab.button.disabled = true;
            tab.button.classList.add('disabled');
            
            // 如果禁用的是当前标签，切换到其他标签
            if (this.currentTab === tabName) {
                const availableTabs = this.getVisibleTabs();
                if (availableTabs.length > 0) {
                    this.switchTab(availableTabs[0].name);
                }
            }
            return true;
        }
        return false;
    }

    showTab(tabName) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            tab.visible = true;
            tab.button.classList.remove('hidden');
            tab.button.style.display = '';
            return true;
        }
        return false;
    }

    hideTab(tabName) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            tab.visible = false;
            tab.button.classList.add('hidden');
            tab.button.style.display = 'none';
            
            // 如果隐藏的是当前标签，切换到其他标签
            if (this.currentTab === tabName) {
                const availableTabs = this.getVisibleTabs();
                if (availableTabs.length > 0) {
                    this.switchTab(availableTabs[0].name);
                }
            }
            return true;
        }
        return false;
    }

    updateTabTitle(tabName, newTitle) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            tab.title = newTitle;
            tab.button.textContent = newTitle;
            return true;
        }
        return false;
    }

    addBadge(tabName, badge) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            let badgeElement = tab.button.querySelector('.tab-badge');
            if (!badgeElement) {
                badgeElement = document.createElement('span');
                badgeElement.className = 'tab-badge';
                badgeElement.style.cssText = `
                    margin-left: var(--spacing-sm);
                    background-color: var(--color-primary);
                    color: white;
                    font-size: var(--font-size-xs);
                    padding: 2px var(--spacing-xs);
                    border-radius: var(--border-radius-lg);
                    min-width: 18px;
                    text-align: center;
                `;
                tab.button.appendChild(badgeElement);
            }
            badgeElement.textContent = badge;
            return true;
        }
        return false;
    }

    removeBadge(tabName) {
        const tab = this.tabs.get(tabName);
        if (tab) {
            const badgeElement = tab.button.querySelector('.tab-badge');
            if (badgeElement) {
                badgeElement.remove();
                return true;
            }
        }
        return false;
    }

    refresh() {
        this.tabs.clear();
        this.collectTabs();
        this.setupEventListeners();
        
        // 保持当前标签或切换到默认标签
        if (this.currentTab && this.tabs.has(this.currentTab)) {
            this.switchTab(this.currentTab, false);
        } else {
            this.initializeDefaultTab();
        }
    }

    destroy() {
        // 移除所有事件监听器
        this.tabs.forEach((tab) => {
            tab.button.replaceWith(tab.button.cloneNode(true));
        });
        
        this.tabs.clear();
        this.history = [];
        this.currentTab = null;
    }

    // 事件监听器
    onTabChange(callback) {
        document.addEventListener('tabChanged', callback);
    }

    offTabChange(callback) {
        document.removeEventListener('tabChanged', callback);
    }
}

// 全局注册组件
if (typeof window !== 'undefined') {
    window.TabManager = TabManager;
    
    // 创建全局实例（向后兼容）
    window.switchTab = function(tabName) {
        if (window.globalTabManager) {
            window.globalTabManager.switchTab(tabName);
        } else {
            console.warn('Global TabManager not initialized');
        }
    };
}