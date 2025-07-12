#!/usr/bin/env python3
"""
智能网站爬虫 Web 服务器
提供 REST API 和 WebSocket 支持
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import queue
import time

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

# 爬虫相关导入
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
    from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
    from crawl4ai.deep_crawling.filters import DomainFilter, URLPatternFilter, FilterChain
    from crawl4ai import LLMConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("警告: crawl4ai 未安装，请运行 'pip install crawl4ai'")

# 内容过滤器导入
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from content_filter import ContentFilter, create_default_filter
    CONTENT_FILTER_AVAILABLE = True
    print("✅ 内容过滤器已加载")
except ImportError:
    CONTENT_FILTER_AVAILABLE = False
    print("警告: 内容过滤器不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
tasks: Dict[str, Dict] = {}  # 存储任务状态
task_queue = queue.Queue()   # 任务队列
results_storage: Dict[str, List] = {}  # 结果存储


class CrawlerTask:
    """爬虫任务类"""
    
    def __init__(self, task_id: str, config: Dict):
        self.task_id = task_id
        self.config = config
        self.status = 'pending'
        self.progress = 0
        self.status_text = '等待开始...'
        self.stats = {
            'discovered': 0,
            'crawled': 0,
            'failed': 0,
            'filtered': 0
        }
        self.results = []
        self.navigation = []
        self.error = None
        self.start_time = None
        self.end_time = None
        
        # 存储发现的URL和内容
        self.discovered_urls = set()
        self.crawled_content = {}

    def update_status(self, status: str, progress: int = None, status_text: str = None):
        """更新任务状态"""
        self.status = status
        if progress is not None:
            self.progress = progress
        if status_text:
            self.status_text = status_text
            
        # 通过WebSocket发送更新
        socketio.emit('task_update', {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'status_text': self.status_text,
            'stats': self.stats
        })

    def add_log(self, message: str, level: str = 'info'):
        """添加日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'level': level
        }
        
        socketio.emit('log', log_entry)
        logger.info(f"[{self.task_id}] {message}")

    def add_result(self, result: Dict):
        """添加结果"""
        self.results.append(result)
        self.stats['crawled'] = len(self.results)
        
        socketio.emit('result', {
            'task_id': self.task_id,
            'result': result
        })

    async def run(self):
        """执行爬虫任务"""
        if not CRAWL4AI_AVAILABLE:
            self.status = 'failed'
            self.error = 'crawl4ai 未安装'
            return

        try:
            self.start_time = datetime.now()
            self.update_status('running', 0, '初始化爬虫...')
            self.add_log('开始执行爬虫任务')

            # 第一步：发现网站结构
            await self.discover_website_structure()
            
            # 第二步：抓取所有内容
            await self.crawl_all_content()
            
            # 第三步：生成导航结构
            self.generate_navigation_structure()
            
            # 完成
            self.end_time = datetime.now()
            self.update_status('completed', 100, '抓取完成')
            self.add_log('爬虫任务执行完成', 'success')
            
        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
            self.add_log(f'任务执行失败: {str(e)}', 'error')
            logger.error(f"任务 {self.task_id} 失败: {str(e)}", exc_info=True)

    async def discover_website_structure(self):
        """发现网站结构"""
        self.update_status('running', 10, '发现网站结构...')
        self.add_log('开始发现网站结构')
        
        config = self.config
        browser_config = self._create_browser_config()
        
        # 配置过滤器
        filters = []
        if config['filters']['exclude_domains']:
            domain_filter = DomainFilter(
                blocked_domains=config['filters']['exclude_domains']
            )
            filters.append(domain_filter)
        
        if config['filters']['exclude_patterns']:
            pattern_filter = URLPatternFilter(
                excluded_patterns=config['filters']['exclude_patterns']
            )
            filters.append(pattern_filter)
        
        # 总是创建 FilterChain，即使没有过滤器也创建空的
        filter_chain = FilterChain(filters)
        
        # 配置深度爬取策略
        deep_crawl_strategy = None
        if config['crawl_strategy'] == 'bfs':
            deep_crawl_strategy = BFSDeepCrawlStrategy(
                max_depth=config['max_depth'],
                include_external=False,
                max_pages=config['max_pages'],
                filter_chain=filter_chain
            )
        elif config['crawl_strategy'] == 'dfs':
            deep_crawl_strategy = DFSDeepCrawlStrategy(
                max_depth=config['max_depth'],
                include_external=False,
                max_pages=config['max_pages'],
                filter_chain=filter_chain
            )
        
        # 配置爬取参数
        run_config = CrawlerRunConfig(
            cache_mode=getattr(CacheMode, config['cache_mode']),
            deep_crawl_strategy=deep_crawl_strategy,
            exclude_external_links=config['filters']['exclude_external'],
            exclude_social_media_links=config['filters']['exclude_social'],
            exclude_external_images=config['filters']['exclude_images'],
            process_iframes=config['filters']['process_iframes'],
            word_count_threshold=config['word_threshold'],
            wait_for=config['wait_for'],
            stream=True
        )
        
        discovered_urls = [config['target_url']]
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            try:
                if deep_crawl_strategy:
                    # 使用深度爬取
                    async for result in await crawler.arun(
                        url=config['target_url'],
                        config=run_config
                    ):
                        if result.success:
                            current_url = result.url
                            discovered_urls.append(current_url)
                            self.discovered_urls.add(current_url)
                            
                            # 提取内部链接
                            internal_links = result.links.get("internal", [])
                            for link in internal_links:
                                link_url = link.get("href", "")
                                if link_url and self._is_valid_url(link_url, config['target_url']):
                                    discovered_urls.append(link_url)
                                    self.discovered_urls.add(link_url)
                            
                            self.add_log(f'发现页面: {current_url} (内部链接: {len(internal_links)})')
                        else:
                            self.add_log(f'页面发现失败: {result.url}', 'warning')
                else:
                    # 仅抓取首页链接
                    result = await crawler.arun(url=config['target_url'], config=run_config)
                    if result.success:
                        internal_links = result.links.get("internal", [])
                        for link in internal_links:
                            link_url = link.get("href", "")
                            if link_url and self._is_valid_url(link_url, config['target_url']):
                                discovered_urls.append(link_url)
                                self.discovered_urls.add(link_url)
                        
                        self.add_log(f'在首页发现 {len(internal_links)} 个内部链接')
                    
            except Exception as e:
                self.add_log(f'网站结构发现出错: {str(e)}', 'error')
                raise
        
        # 去重并排序
        unique_urls = list(set(discovered_urls))
        unique_urls.sort()
        
        self.stats['discovered'] = len(unique_urls)
        self.update_status('running', 30, f'发现 {len(unique_urls)} 个页面')
        self.add_log(f'网站结构发现完成，共发现 {len(unique_urls)} 个页面')
        
        return unique_urls

    async def crawl_all_content(self):
        """抓取所有内容"""
        urls = list(self.discovered_urls)
        if not urls:
            urls = [self.config['target_url']]
        
        self.update_status('running', 40, f'开始抓取 {len(urls)} 个页面的内容...')
        self.add_log(f'开始批量抓取内容，共 {len(urls)} 个页面')
        
        browser_config = self._create_browser_config()
        extraction_strategy = self._create_extraction_strategy()
        
        run_config = CrawlerRunConfig(
            cache_mode=getattr(CacheMode, self.config['cache_mode']),
            extraction_strategy=extraction_strategy,
            exclude_external_links=self.config['filters']['exclude_external'],
            exclude_social_media_links=self.config['filters']['exclude_social'],
            word_count_threshold=self.config['word_threshold'],
            screenshot='screenshot' in self.config['output_formats'],
            pdf='pdf' in self.config['output_formats']
        )
        
        successful_crawls = 0
        failed_crawls = 0
        batch_size = self.config['batch_size']
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(urls) + batch_size - 1) // batch_size
                
                progress = 40 + int((i / len(urls)) * 50)
                self.update_status('running', progress, f'处理批次 {batch_num}/{total_batches}')
                self.add_log(f'处理批次 {batch_num}/{total_batches}')
                
                try:
                    results = await crawler.arun_many(urls=batch_urls, config=run_config)
                    
                    for result in results:
                        if result.success:
                            content_data = self._process_crawl_result(result)
                            self.add_result(content_data)
                            successful_crawls += 1
                            self.add_log(f'成功抓取: {result.url}')
                        else:
                            failed_crawls += 1
                            self.add_log(f'抓取失败: {result.url}', 'warning')
                
                except Exception as e:
                    self.add_log(f'批次处理出错: {str(e)}', 'error')
                    failed_crawls += len(batch_urls)
                
                # 短暂延迟
                await asyncio.sleep(self.config['delay'])
        
        self.stats['crawled'] = successful_crawls
        self.stats['failed'] = failed_crawls
        
        self.update_status('running', 90, '处理抓取结果...')
        self.add_log(f'内容抓取完成! 成功: {successful_crawls}, 失败: {failed_crawls}')

    def generate_navigation_structure(self):
        """生成导航结构"""
        self.add_log('生成导航结构...')
        
        # 提取真实的导航栏内容
        navigation = []
        navigation_items = set()  # 用于去重
        
        for result in self.results:
            # 从提取的内容中获取导航栏信息
            extracted_content = result.get('extracted_content', {})
            
            # 处理导航栏内容
            nav_content = None
            if isinstance(extracted_content, list) and len(extracted_content) > 0:
                nav_content = extracted_content[0].get('navigation', '')
            elif isinstance(extracted_content, dict):
                nav_content = extracted_content.get('navigation', '')
            
            # 如果有导航栏内容，解析其中的链接
            if nav_content:
                nav_links = self._extract_navigation_links(nav_content, result['url'])
                for link in nav_links:
                    link_key = f"{link['title']}|{link['url']}"
                    if link_key not in navigation_items:
                        navigation_items.add(link_key)
                        navigation.append(link)
            
            # 同时保留基于URL路径的导航项
            nav_item = {
                'url': result['url'],
                'title': result['title'] or '无标题',
                'path': result['url'].replace(self.config['target_url'], ''),
                'level': result['url'].count('/') - 2,  # 估算层级
                'type': 'page'  # 标记为页面类型
            }
            navigation.append(nav_item)
        
        # 按照层级和路径排序
        navigation.sort(key=lambda x: (x.get('level', 0), x.get('path', x['url'])))
        self.navigation = navigation

    def _create_browser_config(self) -> BrowserConfig:
        """创建浏览器配置"""
        browser_config = self.config['browser']
        
        # 确保 user_agent 不为 None，提供默认值
        user_agent = browser_config.get('user_agent')
        if not user_agent:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        return BrowserConfig(
            headless=browser_config.get('headless', True),
            verbose=browser_config.get('verbose', False),
            user_agent=user_agent,
            proxy=browser_config.get('proxy')
        )

    def _create_extraction_strategy(self):
        """创建提取策略"""
        extraction = self.config['extraction']
        
        if extraction['type'] == 'css' and extraction['css_selectors']:
            return JsonCssExtractionStrategy(extraction['css_selectors'])
        elif extraction['type'] == 'llm' and extraction['llm_api_key']:
            llm_config = LLMConfig(
                provider=extraction['llm_provider'],
                api_token=extraction['llm_api_key']
            )
            return LLMExtractionStrategy(
                llm_config=llm_config,
                instruction=extraction['llm_instruction'] or "提取页面的主要内容",
                extraction_type="json"
            )
        
        return None

    def _process_crawl_result(self, result) -> Dict:
        """处理爬取结果"""
        content_data = {
            'url': result.url,
            'title': '',
            'description': '',
            'timestamp': datetime.now().isoformat(),
            'status_code': result.status_code,
            'markdown': str(result.markdown) if result.markdown else '',
            'links_count': len(result.links.get('internal', [])),
            'extracted_content': {}
        }
        
        # 处理提取的结构化内容
        if result.extracted_content:
            try:
                extracted = json.loads(result.extracted_content)
                content_data['extracted_content'] = extracted
                
                # 提取标题和描述
                if extracted and len(extracted) > 0:
                    first_item = extracted[0] if isinstance(extracted, list) else extracted
                    content_data['title'] = first_item.get('title', '')
                    content_data['description'] = first_item.get('description', '')
            except json.JSONDecodeError:
                pass
        
        # 如果没有从提取内容中获得标题，尝试从URL推断
        if not content_data['title']:
            content_data['title'] = result.url.split('/')[-1] or 'Home'
        
        return content_data

    def _extract_navigation_links(self, nav_content: str, base_url: str) -> List[Dict]:
        """从导航栏内容中提取链接"""
        import re
        from urllib.parse import urljoin, urlparse
        
        nav_links = []
        
        # 使用正则表达式提取链接
        # 匹配 markdown 链接格式 [text](url)
        markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', nav_content)
        for text, url in markdown_links:
            full_url = urljoin(base_url, url)
            if self._is_valid_url(full_url, self.config['target_url']):
                nav_links.append({
                    'title': text.strip(),
                    'url': full_url,
                    'type': 'navigation',
                    'level': 0
                })
        
        # 匹配 HTML 链接格式 <a href="url">text</a>
        html_links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', nav_content, re.IGNORECASE)
        for url, text in html_links:
            full_url = urljoin(base_url, url)
            if self._is_valid_url(full_url, self.config['target_url']):
                nav_links.append({
                    'title': text.strip(),
                    'url': full_url,
                    'type': 'navigation',
                    'level': 0
                })
        
        # 去重
        unique_links = []
        seen = set()
        for link in nav_links:
            key = f"{link['title']}|{link['url']}"
            if key not in seen:
                seen.add(key)
                unique_links.append(link)
        
        return unique_links

    def _is_valid_url(self, url: str, base_url: str) -> bool:
        """检查URL是否有效"""
        try:
            from urllib.parse import urlparse
            base_parsed = urlparse(base_url)
            url_parsed = urlparse(url)
            
            return (
                url_parsed.netloc == base_parsed.netloc and
                url_parsed.scheme in ['http', 'https'] and
                not any(ext in url.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js'])
            )
        except:
            return False

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'progress': self.progress,
            'status_text': self.status_text,
            'stats': self.stats,
            'results': self.results,
            'navigation': self.navigation,
            'error': self.error,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


def task_worker():
    """任务工作线程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:  # 退出信号
                break
            
            # 运行异步任务
            loop.run_until_complete(task.run())
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"任务工作线程错误: {str(e)}", exc_info=True)


# 启动工作线程
worker_thread = threading.Thread(target=task_worker, daemon=True)
worker_thread.start()


@app.route('/')
def index():
    """主页"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    """静态文件"""
    return send_from_directory('.', filename)


@app.route('/api/crawl', methods=['POST'])
def start_crawl():
    """启动爬取任务"""
    try:
        config = request.get_json()
        
        # 验证配置
        if not config or not config.get('target_url'):
            return jsonify({'success': False, 'error': '缺少目标URL'}), 400
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task = CrawlerTask(task_id, config)
        tasks[task_id] = task
        
        # 添加到队列
        task_queue.put(task)
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '爬取任务已启动'
        })
        
    except Exception as e:
        logger.error(f"启动爬取任务失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """获取任务状态"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(task.to_dict())


@app.route('/api/results/<task_id>')
def get_task_results(task_id):
    """获取任务结果"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({
        'results': task.results,
        'navigation': task.navigation,
        'stats': task.stats
    })


@app.route('/api/tasks')
def list_tasks():
    """列出所有任务"""
    task_list = []
    for task_id, task in tasks.items():
        task_list.append({
            'task_id': task_id,
            'status': task.status,
            'progress': task.progress,
            'stats': task.stats,
            'start_time': task.start_time.isoformat() if task.start_time else None
        })
    
    return jsonify({'tasks': task_list})


@socketio.on('connect')
def handle_connect():
    """WebSocket连接"""
    emit('connected', {'message': 'WebSocket连接已建立'})


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开"""
    print('客户端断开连接')


if __name__ == '__main__':
    print("🚀 启动智能网站爬虫 Web 服务器...")
    print("📱 Web界面: http://localhost:5000")
    print("🔌 API文档: http://localhost:5000/api/tasks")
    
    if not CRAWL4AI_AVAILABLE:
        print("⚠️  警告: crawl4ai 未安装，请运行 'pip install crawl4ai'")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 