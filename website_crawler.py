#!/usr/bin/env python3
"""
网站内容抓取器
功能：
1. 自动发现网站的所有子页面（导航栏、链接等）
2. 批量抓取所有页面内容并结构化存储
3. 建立URL与内容的映射关系

作者：AITOOLBOX
创建时间：2025年1月
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse
import logging

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import DomainFilter, URLPatternFilter, FilterChain

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 尝试导入增强导航提取器
try:
    from enhanced_navigation_extractor import EnhancedNavigationExtractor, enhance_navigation_extraction
    ENHANCED_NAV_AVAILABLE = True
    logger.info("✅ 增强导航提取器已加载")
except ImportError:
    ENHANCED_NAV_AVAILABLE = False
    logger.warning("⚠️  增强导航提取器不可用，将使用基础导航功能")

# 尝试导入内容过滤器
try:
    from content_filter import ContentFilter, create_default_filter
    CONTENT_FILTER_AVAILABLE = True
    logger.info("✅ 内容过滤器已加载")
except ImportError:
    CONTENT_FILTER_AVAILABLE = False
    logger.warning("⚠️  内容过滤器不可用，将不进行内容过滤")


class WebsiteCrawler:
    """网站爬虫类，负责发现和抓取网站内容"""
    
    def __init__(self, base_url: str, output_dir: str = "results", 
                 content_filter_config: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            base_url: 目标网站的基础URL
            output_dir: 输出目录
            content_filter_config: 内容过滤器配置
        """
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 存储发现的URL和内容
        self.discovered_urls: Set[str] = set()
        self.crawled_content: Dict[str, Dict] = {}
        self.url_mapping: Dict[str, str] = {}  # URL到文件路径的映射
        
        # 初始化内容过滤器
        self.content_filter = None
        if CONTENT_FILTER_AVAILABLE and content_filter_config:
            self.content_filter = ContentFilter.create_from_config(content_filter_config)
            logger.info("✅ 内容过滤器已启用")
        elif CONTENT_FILTER_AVAILABLE:
            # 使用默认过滤器
            self.content_filter = create_default_filter()
            logger.info("✅ 使用默认内容过滤器")
        
        # 统计信息
        self.stats = {
            'total_discovered': 0,
            'total_crawled': 0,
            'failed_crawls': 0,
            'filtered_elements': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def discover_website_structure(self, max_depth: int = 3, max_pages: int = 100) -> List[str]:
        """
        第一步：发现网站结构，获取所有可能的页面URL
        
        Args:
            max_depth: 最大爬取深度
            max_pages: 最大页面数量
            
        Returns:
            发现的所有URL列表
        """
        logger.info(f"🔍 开始发现网站结构: {self.base_url}")
        self.stats['start_time'] = datetime.now()
        
        # 配置浏览器
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # 配置域名过滤器，只爬取同域名页面
        domain_filter = DomainFilter(
            allowed_domains=[self.domain],
            blocked_domains=[]
        )
        
        # 配置URL模式过滤器，排除不需要的文件类型
        url_filter = URLPatternFilter(
            excluded_patterns=[
                "*.pdf", "*.jpg", "*.jpeg", "*.png", "*.gif", "*.svg",
                "*.css", "*.js", "*.ico", "*.woff", "*.woff2", "*.ttf",
                "*.zip", "*.tar", "*.gz", "*.mp4", "*.mp3", "*.avi"
            ]
        )
        
        filter_chain = FilterChain([domain_filter, url_filter])
        
        # 配置深度爬取策略
        deep_crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
            max_pages=max_pages,
            filter_chain=filter_chain
        )
        
        # 配置爬取参数
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            deep_crawl_strategy=deep_crawl_strategy,
            exclude_external_links=True,
            exclude_social_media_links=True,
            exclude_domains=["facebook.com", "twitter.com", "instagram.com", "linkedin.com"],
            word_count_threshold=50,  # 过滤太短的内容
            stream=True  # 启用流式处理
        )
        
        discovered_urls = []
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            try:
                # 使用深度爬取发现所有页面
                async for result in await crawler.arun(
                    url=self.base_url,
                    config=run_config
                ):
                    if result.success:
                        current_url = result.url
                        discovered_urls.append(current_url)
                        self.discovered_urls.add(current_url)
                        
                        # 提取页面中的所有内部链接
                        internal_links = result.links.get("internal", [])
                        for link in internal_links:
                            link_url = link.get("href", "")
                            if link_url and link_url not in self.discovered_urls:
                                full_url = urljoin(self.base_url, link_url)
                                if self._is_valid_url(full_url):
                                    discovered_urls.append(full_url)
                                    self.discovered_urls.add(full_url)
                        
                        logger.info(f"✅ 发现页面: {current_url} (内部链接: {len(internal_links)})")
                    else:
                        logger.warning(f"❌ 页面发现失败: {result.url} - {result.error_message}")
            
            except Exception as e:
                logger.error(f"❌ 网站结构发现过程中出错: {str(e)}")
        
        # 去重并排序
        unique_urls = list(set(discovered_urls))
        unique_urls.sort()
        
        self.stats['total_discovered'] = len(unique_urls)
        logger.info(f"🎉 网站结构发现完成! 共发现 {len(unique_urls)} 个页面")
        
        # 保存发现的URL列表
        self._save_discovered_urls(unique_urls)
        
        return unique_urls
    
    async def crawl_all_content(self, urls: List[str], batch_size: int = 10) -> Dict[str, Any]:
        """
        第二步：批量抓取所有页面内容
        
        Args:
            urls: 要抓取的URL列表
            batch_size: 批处理大小
            
        Returns:
            抓取结果统计
        """
        logger.info(f"📥 开始批量抓取内容，共 {len(urls)} 个页面")
        
        # 配置浏览器
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # 配置内容提取策略
        extraction_schema = {
            "name": "PageContent",
            "baseSelector": "body",
            "fields": [
                {"name": "title", "selector": "title, h1", "type": "text"},
                {"name": "description", "selector": "meta[name='description']", "type": "attribute", "attribute": "content"},
                {"name": "headings", "selector": "h1, h2, h3, h4, h5, h6", "type": "text"},
                {"name": "main_content", "selector": "main, article, .content, .main-content", "type": "text"},
                {"name": "navigation", "selector": "nav, .nav, .navigation, .navbar, .menu, .sidebar, [role='navigation'], .nav-menu, .main-nav, .site-nav, .primary-nav, .header-nav, .top-nav, .side-nav, .navigation-menu", "type": "html"},
                {"name": "navigation_links", "selector": "nav a, .nav a, .navigation a, .navbar a, .menu a, .sidebar a, [role='navigation'] a, .nav-menu a, .main-nav a, .site-nav a, .primary-nav a, .header-nav a, .top-nav a, .side-nav a, .navigation-menu a", "type": "text", "attribute": "href"}
            ]
        }
        
        extraction_strategy = JsonCssExtractionStrategy(extraction_schema)
        
        # 配置爬取参数
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            exclude_external_links=True,
            exclude_social_media_links=True,
            word_count_threshold=10,
            screenshot=False,  # 可选：是否截图
            markdown_generator=None  # 使用默认Markdown生成器
        )
        
        # 分批处理URL
        successful_crawls = 0
        failed_crawls = 0
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                logger.info(f"📦 处理批次 {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
                
                try:
                    # 批量爬取
                    results = await crawler.arun_many(
                        urls=batch_urls,
                        config=run_config
                    )
                    
                    # 处理结果
                    for result in results:
                        if result.success:
                            await self._process_crawl_result(result)
                            successful_crawls += 1
                            logger.info(f"✅ 内容抓取成功: {result.url}")
                        else:
                            failed_crawls += 1
                            logger.warning(f"❌ 内容抓取失败: {result.url} - {result.error_message}")
                
                except Exception as e:
                    logger.error(f"❌ 批次处理出错: {str(e)}")
                    failed_crawls += len(batch_urls)
                
                # 短暂延迟，避免过于频繁的请求
                await asyncio.sleep(1)
        
        self.stats['total_crawled'] = successful_crawls
        self.stats['failed_crawls'] = failed_crawls
        self.stats['end_time'] = datetime.now()
        
        logger.info(f"🎉 内容抓取完成! 成功: {successful_crawls}, 失败: {failed_crawls}")
        
        # 保存最终结果
        await self._save_final_results()
        
        return {
            'successful_crawls': successful_crawls,
            'failed_crawls': failed_crawls,
            'total_content_items': len(self.crawled_content),
            'output_directory': str(self.output_dir.absolute())
        }
    
    async def _process_crawl_result(self, result) -> None:
        """处理单个爬取结果"""
        url = result.url
        
        # 生成安全的文件名
        safe_filename = self._url_to_filename(url)
        
        # 应用内容过滤
        cleaned_html = result.cleaned_html
        markdown_content = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown)
        
        if self.content_filter:
            # 过滤HTML内容
            filtered_html = self.content_filter.filter_html(cleaned_html)
            if filtered_html != cleaned_html:
                self.stats['filtered_elements'] += 1
                logger.info(f"已对页面 {url} 应用内容过滤")
                cleaned_html = filtered_html
            
            # 过滤Markdown内容
            filtered_markdown = self.content_filter.filter_text(markdown_content)
            if filtered_markdown != markdown_content:
                markdown_content = filtered_markdown
        
        # 提取内容
        content_data = {
            'url': url,
            'title': '',
            'description': '',
            'timestamp': datetime.now().isoformat(),
            'status_code': result.status_code,
            'markdown': markdown_content,
            'cleaned_html': cleaned_html,
            'extracted_content': {},
            'links': result.links,
            'media': result.media,
            'content_filtered': bool(self.content_filter)
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
                    
                    # 专门处理导航栏内容
                    nav_html = first_item.get('navigation', '')
                    nav_links = first_item.get('navigation_links', [])
                    
                    if nav_html or nav_links:
                        content_data['navigation_data'] = {
                            'html': nav_html,
                            'links': nav_links,
                            'extracted_links': self._extract_navigation_links(nav_html, url) if nav_html else []
                        }
            except json.JSONDecodeError:
                logger.warning(f"⚠️ 无法解析提取的内容: {url}")
        
        # 保存到内存
        self.crawled_content[url] = content_data
        
        # 保存到文件
        content_file = self.output_dir / "content" / f"{safe_filename}.json"
        content_file.parent.mkdir(exist_ok=True)
        
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(content_data, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown文件
        markdown_file = self.output_dir / "markdown" / f"{safe_filename}.md"
        markdown_file.parent.mkdir(exist_ok=True)
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# {content_data['title']}\n\n")
            f.write(f"**URL**: {url}\n")
            f.write(f"**抓取时间**: {content_data['timestamp']}\n\n")
            f.write("---\n\n")
            f.write(content_data['markdown'])
        
        # 更新URL映射
        self.url_mapping[url] = str(content_file.relative_to(self.output_dir))
    
    def _extract_navigation_links(self, nav_html: str, base_url: str) -> List[Dict]:
        """从导航栏HTML中提取链接"""
        import re
        from urllib.parse import urljoin
        
        nav_links = []
        
        # 使用正则表达式提取HTML链接
        html_links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', nav_html, re.IGNORECASE)
        for url, text in html_links:
            full_url = urljoin(base_url, url)
            if self._is_valid_url(full_url):
                nav_links.append({
                    'title': text.strip(),
                    'url': full_url,
                    'type': 'navigation'
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

    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc == self.domain and
                parsed.scheme in ['http', 'https'] and
                not any(ext in url.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js'])
            )
        except:
            return False
    
    def _url_to_filename(self, url: str) -> str:
        """将URL转换为安全的文件名"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            path = 'index'
        
        # 替换特殊字符
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        filename = ''.join(c if c in safe_chars else '_' for c in path)
        
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename or 'page'
    
    def _save_discovered_urls(self, urls: List[str]) -> None:
        """保存发现的URL列表"""
        urls_file = self.output_dir / "discovered_urls.json"
        urls_data = {
            'base_url': self.base_url,
            'discovery_time': datetime.now().isoformat(),
            'total_count': len(urls),
            'urls': urls
        }
        
        with open(urls_file, 'w', encoding='utf-8') as f:
            json.dump(urls_data, f, ensure_ascii=False, indent=2)
        
        # 同时保存为文本文件，便于查看
        txt_file = self.output_dir / "discovered_urls.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"网站: {self.base_url}\n")
            f.write(f"发现时间: {urls_data['discovery_time']}\n")
            f.write(f"总计: {len(urls)} 个页面\n\n")
            for i, url in enumerate(urls, 1):
                f.write(f"{i:3d}. {url}\n")
    
    async def _save_final_results(self) -> None:
        """保存最终结果和统计信息"""
        # 保存统计信息
        stats_file = self.output_dir / "crawl_stats.json"
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds() if self.stats['end_time'] and self.stats['start_time'] else 0
        
        final_stats = {
            **self.stats,
            'duration_seconds': duration,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
            'base_url': self.base_url,
            'domain': self.domain,
            'enhanced_navigation_enabled': ENHANCED_NAV_AVAILABLE
        }
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(final_stats, f, ensure_ascii=False, indent=2)
        
        # 保存URL映射
        mapping_file = self.output_dir / "url_mapping.json"
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.url_mapping, f, ensure_ascii=False, indent=2)
        
        # 如果启用了增强导航功能，进行导航栏增强处理
        if ENHANCED_NAV_AVAILABLE:
            await self._process_enhanced_navigation()
        
        # 创建索引文件
        await self._create_index_file()
    
    async def _process_enhanced_navigation(self) -> None:
        """处理增强导航功能"""
        if not ENHANCED_NAV_AVAILABLE:
            return
        
        logger.info("🔍 开始处理增强导航功能...")
        
        try:
            # 准备爬取结果数据
            crawl_results = []
            for url, content in self.crawled_content.items():
                crawl_result = {
                    'url': url,
                    'title': content.get('title', ''),
                    'html_content': content.get('html', ''),
                    'navigation': content.get('navigation', ''),
                    'navigation_links': content.get('navigation_links', [])
                }
                crawl_results.append(crawl_result)
            
            # 使用增强导航提取器处理
            enhanced_results = enhance_navigation_extraction(crawl_results, self.base_url)
            
            # 保存增强导航结果
            enhanced_nav_file = self.output_dir / "enhanced_navigation.json"
            with open(enhanced_nav_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 增强导航结果已保存到: {enhanced_nav_file}")
            
            # 生成导航报告
            await self._generate_navigation_report(enhanced_results)
            
        except Exception as e:
            logger.error(f"❌ 增强导航处理失败: {str(e)}")
    
    async def _generate_navigation_report(self, enhanced_results: Dict[str, Any]) -> None:
        """生成导航栏分析报告"""
        report_file = self.output_dir / "navigation_report.html"
        
        report_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>导航栏分析报告 - {self.domain}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f0f8ff; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .nav-item {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .nav-item:hover {{ background: #f9f9f9; }}
        .nav-link {{ color: #1976d2; text-decoration: none; }}
        .nav-link:hover {{ text-decoration: underline; }}
        .level-0 {{ margin-left: 0; }}
        .level-1 {{ margin-left: 20px; }}
        .level-2 {{ margin-left: 40px; }}
        .level-3 {{ margin-left: 60px; }}
        .enhanced-badge {{ background: #4caf50; color: white; padding: 2px 6px; border-radius: 3px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>导航栏分析报告 <span class="enhanced-badge">增强版</span></h1>
        <p><strong>网站:</strong> {self.base_url}</p>
        <p><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <h3>统计信息</h3>
        <p>总页面数: <strong>{enhanced_results.get('total_pages', 0)}</strong></p>
        <p>包含导航的页面数: <strong>{enhanced_results.get('pages_with_navigation', 0)}</strong></p>
        <p>唯一导航链接数: <strong>{len(enhanced_results.get('unique_navigation_links', []))}</strong></p>
        <p>增强导航功能: <strong>✅ 已启用</strong></p>
    </div>
    
    <h2>导航结构</h2>
    <div class="navigation-structure">
"""
        
        # 添加导航结构
        for item in enhanced_results.get('navigation_structure', []):
            level_class = f"level-{item.get('level', 0)}"
            report_html += f"""
        <div class="nav-item {level_class}">
            <a href="{item.get('url', '#')}" class="nav-link" target="_blank">
                {item.get('text', 'N/A')}
            </a>
            {f"<small> - 层级: {item.get('level', 0)}</small>" if item.get('level', 0) > 0 else ""}
        </div>
"""
        
        report_html += """
    </div>
    
    <h2>增强功能特性</h2>
    <div class="features">
        <ul>
            <li>✅ 15种专业导航选择器（vs 原来的3种）</li>
            <li>✅ 完整HTML结构保留（vs 原来的纯文本）</li>
            <li>✅ 多层级导航识别</li>
            <li>✅ 智能链接提取和去重</li>
            <li>✅ 导航结构分析和报告</li>
            <li>✅ 与现有系统完全兼容</li>
        </ul>
    </div>
</body>
</html>
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        logger.info(f"✅ 导航栏分析报告已保存到: {report_file}")
    
    async def _create_index_file(self) -> None:
        """创建索引文件，便于浏览和查找"""
        index_file = self.output_dir / "index.html"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>网站内容抓取结果 - {self.domain}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-item {{ background: #e3f2fd; padding: 10px; border-radius: 5px; text-align: center; }}
        .url-list {{ max-height: 600px; overflow-y: auto; border: 1px solid #ddd; }}
        .url-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .url-item:hover {{ background: #f9f9f9; }}
        .url-link {{ color: #1976d2; text-decoration: none; }}
        .url-link:hover {{ text-decoration: underline; }}
        .search-box {{ width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>网站内容抓取结果</h1>
        <p><strong>目标网站:</strong> {self.base_url}</p>
        <p><strong>抓取时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <h3>{self.stats['total_discovered']}</h3>
            <p>发现页面</p>
        </div>
        <div class="stat-item">
            <h3>{self.stats['total_crawled']}</h3>
            <p>成功抓取</p>
        </div>
        <div class="stat-item">
            <h3>{self.stats['failed_crawls']}</h3>
            <p>失败页面</p>
        </div>
    </div>
    
    <h2>抓取的页面列表</h2>
    <input type="text" class="search-box" placeholder="搜索页面..." onkeyup="filterUrls(this.value)">
    
    <div class="url-list" id="urlList">
"""
        
        for url, content in self.crawled_content.items():
            title = content.get('title', '无标题')
            description = content.get('description', '')[:100] + ('...' if len(content.get('description', '')) > 100 else '')
            
            html_content += f"""
        <div class="url-item" data-url="{url.lower()}" data-title="{title.lower()}">
            <h4><a href="{url}" class="url-link" target="_blank">{title or url}</a></h4>
            <p><strong>URL:</strong> {url}</p>
            {f'<p><strong>描述:</strong> {description}</p>' if description else ''}
            <p>
                <a href="content/{self._url_to_filename(url)}.json">查看JSON</a> | 
                <a href="markdown/{self._url_to_filename(url)}.md">查看Markdown</a>
            </p>
        </div>
"""
        
        html_content += """
    </div>
    
    <script>
        function filterUrls(searchTerm) {
            const items = document.querySelectorAll('.url-item');
            const term = searchTerm.toLowerCase();
            
            items.forEach(item => {
                const url = item.getAttribute('data-url');
                const title = item.getAttribute('data-title');
                
                if (url.includes(term) || title.includes(term)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
        
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)


async def main():
    """主函数示例"""
    # 显示启动信息
    print("🚀 智能网站爬虫启动中...")
    print(f"📊 增强导航功能: {'✅ 已启用' if ENHANCED_NAV_AVAILABLE else '❌ 未启用'}")
    
    if ENHANCED_NAV_AVAILABLE:
        print("🎯 增强导航功能特性:")
        print("   • 15种专业导航选择器（vs 原来的3种）")
        print("   • 完整HTML结构保留（vs 原来的纯文本）")
        print("   • 多层级导航识别")
        print("   • 智能链接提取和去重")
        print("   • 导航结构分析和报告")
    else:
        print("⚠️  要启用增强导航功能，请确保 enhanced_navigation_extractor.py 文件存在")
    
    # 目标网站URL
    target_url = "https://docs.cursor.com/welcome"
    
    # 创建爬虫实例
    crawler = WebsiteCrawler(target_url, "cursor_docs_crawl")
    
    try:
        # 第一步：发现网站结构
        discovered_urls = await crawler.discover_website_structure(
            max_depth=3,  # 最大深度
            max_pages=50  # 最大页面数
        )
        
        print(f"\n🔍 发现的页面数量: {len(discovered_urls)}")
        print("前10个页面:")
        for i, url in enumerate(discovered_urls[:10], 1):
            print(f"  {i:2d}. {url}")
        
        # 第二步：抓取所有内容
        results = await crawler.crawl_all_content(
            discovered_urls,
            batch_size=5  # 批处理大小
        )
        
        print(f"\n📊 抓取结果:")
        print(f"  ✅ 成功抓取: {results['successful_crawls']} 个页面")
        print(f"  ❌ 失败页面: {results['failed_crawls']} 个页面")
        print(f"  📁 输出目录: {results['output_directory']}")
        print(f"  📊 增强导航: {'✅ 已处理' if ENHANCED_NAV_AVAILABLE else '❌ 未处理'}")
        
        if ENHANCED_NAV_AVAILABLE:
            print(f"\n🎉 抓取完成! 请查看输出目录中的以下文件:")
            print(f"  • index.html - 主索引页面")
            print(f"  • enhanced_navigation.json - 增强导航数据")
            print(f"  • navigation_report.html - 导航栏分析报告")
        else:
            print(f"\n🎉 抓取完成! 请查看输出目录中的 index.html 文件")
        
    except Exception as e:
        logger.error(f"❌ 爬虫执行失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 运行爬虫
    asyncio.run(main()) 