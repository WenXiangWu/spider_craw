/**
 * 智能网站爬虫 Web 界面
 * 前端逻辑处理
 */

class CrawlerApp {
    constructor() {
        this.isRunning = false;
        this.currentTask = null;
        this.results = [];
        this.logs = [];
        this.startTime = null;
        
        this.initializeEventListeners();
        this.initializeForm();
        this.setupWebSocket();
    }

    initializeEventListeners() {
        // 表单提交
        document.getElementById('crawlerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startCrawling();
        });

        // 选项卡切换
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // 折叠面板
        document.querySelectorAll('.collapsible').forEach(collapsible => {
            collapsible.addEventListener('click', (e) => {
                this.toggleCollapsible(e.target);
            });
        });

        // 模态框关闭
        document.getElementById('modalClose').addEventListener('click', () => {
            this.closeModal();
        });

        // 提取类型变化
        document.getElementById('extractionType').addEventListener('change', (e) => {
            this.updateExtractionOptions(e.target.value);
        });

        // 点击模态框外部关闭
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('detailModal');
            if (e.target === modal) {
                this.closeModal();
            }
        });
    }

    initializeForm() {
        // 设置默认的CSS选择器配置
        const defaultCssConfig = {
            "name": "PageContent",
            "baseSelector": "body",
            "fields": [
                {"name": "title", "selector": "title, h1", "type": "text"},
                {"name": "description", "selector": "meta[name='description']", "type": "attribute", "attribute": "content"},
                {"name": "headings", "selector": "h1, h2, h3", "type": "text"},
                {"name": "main_content", "selector": "main, article, .content, .main-content", "type": "text"},
                {"name": "navigation", "selector": "nav, .nav, .navigation, .navbar, .menu, .sidebar, [role='navigation'], .nav-menu, .main-nav, .site-nav, .primary-nav, .header-nav, .top-nav, .side-nav, .navigation-menu", "type": "html"}
            ]
        };
        
        document.getElementById('cssSelectors').value = JSON.stringify(defaultCssConfig, null, 2);
        
        // 初始化提取选项显示
        this.updateExtractionOptions('css');
    }

    setupWebSocket() {
        // 建立Socket.IO连接用于实时通信
        try {
            // 使用Socket.IO而不是原生WebSocket
            this.socket = io();
            
            this.socket.on('connect', () => {
                this.addLog('WebSocket连接已建立', 'info');
            });
            
            this.socket.on('task_update', (data) => {
                this.updateProgress(data);
                this.updateStats(data);
            });
            
            this.socket.on('log', (data) => {
                this.addLog(data.message, data.level);
            });
            
            this.socket.on('result', (data) => {
                this.addResult(data.result);
            });
            
            this.socket.on('disconnect', () => {
                this.addLog('WebSocket连接已断开', 'warning');
            });
            
            this.socket.on('connect_error', (error) => {
                this.addLog('WebSocket连接错误，使用HTTP轮询模式', 'warning');
                console.error('Socket.IO error:', error);
            });
        } catch (error) {
            console.log('WebSocket连接失败，将使用HTTP轮询模式');
        }
    }

    async startCrawling() {
        if (this.isRunning) {
            this.addLog('爬虫正在运行中...', 'warning');
            return;
        }

        const config = this.getFormConfig();
        if (!this.validateConfig(config)) {
            return;
        }

        this.isRunning = true;
        this.startTime = Date.now();
        this.results = [];
        this.logs = [];
        
        // 更新UI状态
        this.updateUIState(true);
        this.showProgress();
        this.addLog('开始配置爬虫参数...', 'info');

        try {
            // 发送爬取请求
            const response = await fetch('/api/crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.currentTask = result.task_id;
                this.addLog(`爬取任务已启动，任务ID: ${result.task_id}`, 'success');
                this.pollTaskStatus();
            } else {
                throw new Error(result.error || '启动爬取任务失败');
            }

        } catch (error) {
            this.addLog(`启动失败: ${error.message}`, 'error');
            this.isRunning = false;
            this.updateUIState(false);
            this.hideProgress();
        }
    }

    async pollTaskStatus() {
        if (!this.currentTask || !this.isRunning) return;

        try {
            const response = await fetch(`/api/status/${this.currentTask}`);
            const data = await response.json();

            this.updateProgress(data);
            this.updateStats(data);

            if (data.status === 'completed') {
                this.handleTaskCompletion(data);
            } else if (data.status === 'failed') {
                this.handleTaskFailure(data);
            } else {
                // 继续轮询
                setTimeout(() => this.pollTaskStatus(), 1000);
            }

        } catch (error) {
            this.addLog(`状态查询失败: ${error.message}`, 'error');
            setTimeout(() => this.pollTaskStatus(), 2000);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'progress':
                this.updateProgress(data);
                break;
            case 'log':
                this.addLog(data.message, data.level);
                break;
            case 'result':
                this.addResult(data.result);
                break;
            case 'completed':
                this.handleTaskCompletion(data);
                break;
            case 'error':
                this.addLog(data.message, 'error');
                break;
        }
    }

    handleTaskCompletion(data) {
        this.isRunning = false;
        this.updateUIState(false);
        this.hideProgress();
        
        const duration = Math.round((Date.now() - this.startTime) / 1000);
        this.addLog(`爬取完成! 耗时: ${duration}秒`, 'success');
        
        // 更新最终统计
        this.updateStats(data);
        
        // 加载结果
        this.loadResults(data.results);
        
        // 生成导航结构
        this.generateNavigationTree(data.navigation);
    }

    handleTaskFailure(data) {
        this.isRunning = false;
        this.updateUIState(false);
        this.hideProgress();
        this.addLog(`爬取失败: ${data.error}`, 'error');
    }

    getFormConfig() {
        const formData = new FormData(document.getElementById('crawlerForm'));
        const config = {};

        // 基础配置
        config.target_url = formData.get('targetUrl');
        config.output_dir = formData.get('outputDir') || 'crawl_results';
        config.max_depth = parseInt(formData.get('maxDepth')) || 3;
        config.max_pages = parseInt(formData.get('maxPages')) || 50;
        config.batch_size = parseInt(formData.get('batchSize')) || 5;

        // 爬取策略
        config.crawl_strategy = formData.get('crawlStrategy');
        config.cache_mode = formData.get('cacheMode');
        config.word_threshold = parseInt(formData.get('wordThreshold')) || 20;

        // 输出格式
        config.output_formats = formData.getAll('outputFormats');

        // 过滤选项
        config.filters = {
            exclude_external: formData.getAll('filters').includes('excludeExternal'),
            exclude_social: formData.getAll('filters').includes('excludeSocial'),
            exclude_images: formData.getAll('filters').includes('excludeImages'),
            process_iframes: formData.getAll('filters').includes('processIframes'),
            exclude_domains: this.parseTextList(formData.get('excludeDomains')),
            exclude_patterns: this.parseTextList(formData.get('excludePatterns'))
        };

        // 浏览器配置
        config.browser = {
            type: formData.get('browserType'),
            headless: formData.getAll('browserOptions').includes('headless'),
            verbose: formData.getAll('browserOptions').includes('verbose'),
            user_agent: formData.get('userAgent') || null,
            proxy: formData.get('proxy') || null
        };

        // 提取策略
        config.extraction = {
            type: formData.get('extractionType'),
            css_selectors: this.parseCssSelectors(formData.get('cssSelectors')),
            llm_provider: formData.get('llmProvider'),
            llm_api_key: formData.get('llmApiKey'),
            llm_instruction: formData.get('llmInstruction')
        };

        // 等待条件
        config.wait_for = formData.get('waitFor') || null;
        config.delay = parseFloat(formData.get('delay')) || 1;

        return config;
    }

    validateConfig(config) {
        if (!config.target_url) {
            this.addLog('请输入目标网站URL', 'error');
            return false;
        }

        try {
            new URL(config.target_url);
        } catch {
            this.addLog('请输入有效的URL', 'error');
            return false;
        }

        if (config.extraction.type === 'css' && !config.extraction.css_selectors) {
            this.addLog('CSS选择器配置无效', 'error');
            return false;
        }

        if (config.extraction.type === 'llm' && !config.extraction.llm_api_key) {
            this.addLog('使用LLM提取策略需要提供API密钥', 'error');
            return false;
        }

        return true;
    }

    parseTextList(text) {
        if (!text) return [];
        return text.split(',').map(item => item.trim()).filter(item => item);
    }

    parseCssSelectors(text) {
        if (!text) return null;
        try {
            return JSON.parse(text);
        } catch {
            return null;
        }
    }

    updateExtractionOptions(type) {
        // 隐藏所有选项
        document.getElementById('cssSelectorsGroup').style.display = 'none';
        document.getElementById('llmConfigGroup').style.display = 'none';
        document.getElementById('llmApiKeyGroup').style.display = 'none';
        document.getElementById('llmInstructionGroup').style.display = 'none';

        // 显示相应选项
        switch (type) {
            case 'css':
            case 'xpath':
                document.getElementById('cssSelectorsGroup').style.display = 'block';
                break;
            case 'llm':
                document.getElementById('llmConfigGroup').style.display = 'block';
                document.getElementById('llmApiKeyGroup').style.display = 'block';
                document.getElementById('llmInstructionGroup').style.display = 'block';
                break;
        }
    }

    updateUIState(isRunning) {
        const startBtn = document.getElementById('startBtn');
        const form = document.getElementById('crawlerForm');
        
        if (isRunning) {
            startBtn.disabled = true;
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 抓取中...';
            form.classList.add('disabled');
        } else {
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="fas fa-play"></i> 开始抓取';
            form.classList.remove('disabled');
        }
    }

    showProgress() {
        document.getElementById('progressContainer').style.display = 'block';
        document.getElementById('logsContainer').style.display = 'block';
    }

    hideProgress() {
        document.getElementById('progressContainer').style.display = 'none';
    }

    updateProgress(data) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (data.progress !== undefined) {
            progressFill.style.width = `${data.progress}%`;
        }
        
        if (data.status_text) {
            progressText.textContent = data.status_text;
        }
    }

    updateStats(data) {
        if (data.stats) {
            document.getElementById('discoveredCount').textContent = data.stats.discovered || 0;
            document.getElementById('crawledCount').textContent = data.stats.crawled || 0;
            document.getElementById('failedCount').textContent = data.stats.failed || 0;
        }
        
        if (this.startTime) {
            const duration = Math.round((Date.now() - this.startTime) / 1000);
            document.getElementById('duration').textContent = `${duration}s`;
        }
    }

    addLog(message, level = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = {
            timestamp,
            message,
            level
        };
        
        this.logs.push(logEntry);
        
        const logsContainer = document.getElementById('logsContainer');
        const logElement = document.createElement('div');
        logElement.className = `log-entry log-${level}`;
        logElement.textContent = `[${timestamp}] ${message}`;
        
        logsContainer.appendChild(logElement);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    addResult(result) {
        this.results.push(result);
        this.renderResults();
    }

    loadResults(results) {
        this.results = results || [];
        this.renderResults();
    }

    renderResults() {
        const resultsGrid = document.getElementById('resultsGrid');
        
        if (this.results.length === 0) {
            resultsGrid.innerHTML = `
                <div style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 15px;"></i>
                    <p>还没有抓取结果</p>
                </div>
            `;
            return;
        }

        resultsGrid.innerHTML = this.results.map((result, index) => `
            <div class="result-item">
                <div class="result-header">
                    <div>
                        <div class="result-title">${result.title || '无标题'}</div>
                        <div class="result-url">${result.url}</div>
                    </div>
                </div>
                <div class="result-actions">
                    <button class="btn-small btn-primary" onclick="app.viewDetails(${index})">
                        <i class="fas fa-eye"></i> 查看详情
                    </button>
                    <button class="btn-small btn-secondary" onclick="app.viewMarkdown(${index})">
                        <i class="fas fa-file-alt"></i> Markdown
                    </button>
                    <button class="btn-small btn-success" onclick="app.viewJson(${index})">
                        <i class="fas fa-code"></i> JSON
                    </button>
                </div>
            </div>
        `).join('');
    }

    generateNavigationTree(navigation) {
        const navTree = document.getElementById('navigationTree');
        
        if (!navigation || navigation.length === 0) {
            navTree.innerHTML = `
                <div style="text-align: center; color: #999; padding: 40px;">
                    <i class="fas fa-sitemap" style="font-size: 3rem; margin-bottom: 15px;"></i>
                    <p>没有发现导航结构</p>
                </div>
            `;
            return;
        }

        // 构建导航树
        const tree = this.buildNavigationTree(navigation);
        navTree.innerHTML = this.renderNavigationTree(tree);
    }

    buildNavigationTree(navigation) {
        // 这里实现导航结构的层级分析
        // 根据URL路径和页面标题构建树形结构
        const tree = [];
        
        navigation.forEach(item => {
            const pathParts = new URL(item.url).pathname.split('/').filter(part => part);
            let currentLevel = tree;
            
            pathParts.forEach((part, index) => {
                let existing = currentLevel.find(node => node.name === part);
                if (!existing) {
                    existing = {
                        name: part,
                        url: index === pathParts.length - 1 ? item.url : null,
                        title: index === pathParts.length - 1 ? item.title : part,
                        children: []
                    };
                    currentLevel.push(existing);
                }
                currentLevel = existing.children;
            });
        });
        
        return tree;
    }

    renderNavigationTree(tree, level = 0) {
        return `
            <ul style="list-style: none; padding-left: ${level * 20}px;">
                ${tree.map(node => `
                    <li style="margin: 5px 0;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            ${node.children.length > 0 ? '<i class="fas fa-folder"></i>' : '<i class="fas fa-file"></i>'}
                            ${node.url ? 
                                `<a href="${node.url}" target="_blank" style="color: #667eea; text-decoration: none;">${node.title}</a>` : 
                                `<span style="font-weight: 500;">${node.title}</span>`
                            }
                        </div>
                        ${node.children.length > 0 ? this.renderNavigationTree(node.children, level + 1) : ''}
                    </li>
                `).join('')}
            </ul>
        `;
    }

    switchTab(tabName) {
        // 更新选项卡样式
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    }

    toggleCollapsible(element) {
        element.classList.toggle('active');
        const content = element.nextElementSibling;
        
        if (content.style.display === 'block') {
            content.style.display = 'none';
            element.querySelector('i').className = 'fas fa-chevron-down';
        } else {
            content.style.display = 'block';
            element.querySelector('i').className = 'fas fa-chevron-up';
        }
    }

    viewDetails(index) {
        const result = this.results[index];
        this.showModal('页面详情', `
            <h3>${result.title || '无标题'}</h3>
            <p><strong>URL:</strong> <a href="${result.url}" target="_blank">${result.url}</a></p>
            <p><strong>抓取时间:</strong> ${result.timestamp}</p>
            <p><strong>状态码:</strong> ${result.status_code}</p>
            <p><strong>内部链接数:</strong> ${result.links_count || 0}</p>
            
            <h4>页面描述</h4>
            <p>${result.description || '无描述'}</p>
            
            <h4>主要内容预览</h4>
            <div style="max-height: 300px; overflow-y: auto; background: #f5f5f5; padding: 15px; border-radius: 8px;">
                <pre style="white-space: pre-wrap; font-size: 13px;">${result.markdown ? result.markdown.substring(0, 1000) + (result.markdown.length > 1000 ? '...' : '') : '无内容'}</pre>
            </div>
        `);
    }

    viewMarkdown(index) {
        const result = this.results[index];
        this.showModal('Markdown 内容', `
            <h3>${result.title || '无标题'}</h3>
            <div style="max-height: 500px; overflow-y: auto;">
                <pre><code class="language-markdown">${result.markdown || '无Markdown内容'}</code></pre>
            </div>
        `);
    }

    viewJson(index) {
        const result = this.results[index];
        this.showModal('JSON 数据', `
            <h3>${result.title || '无标题'}</h3>
            <div style="max-height: 500px; overflow-y: auto;">
                <pre><code class="language-json">${JSON.stringify(result, null, 2)}</code></pre>
            </div>
        `);
    }

    showModal(title, content) {
        const modal = document.getElementById('detailModal');
        const modalContent = document.getElementById('modalContent');
        
        modalContent.innerHTML = `<h2>${title}</h2>${content}`;
        modal.style.display = 'block';
        
        // 高亮代码
        setTimeout(() => {
            if (window.Prism) {
                Prism.highlightAll();
            }
        }, 100);
    }

    closeModal() {
        document.getElementById('detailModal').style.display = 'none';
    }
}

// 初始化应用
const app = new CrawlerApp(); 