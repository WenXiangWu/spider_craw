#!/usr/bin/env python3
"""
内容过滤器模块
功能：
1. 过滤页面中不需要的内容（如页脚、广告、导航等）
2. 支持CSS选择器、XPath和关键词过滤
3. 提供预设的常用过滤规则

作者：AITOOLBOX
创建时间：2025年1月
"""

import re
from typing import List, Dict, Set, Optional
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)


class ContentFilter:
    """内容过滤器类"""
    
    # 预设的常用过滤规则
    PRESET_FILTERS = {
        'footer': {
            'name': '页脚',
            'selectors': [
                'footer', '.footer', '#footer', '.site-footer', '.page-footer',
                '.footer-content', '.footer-wrapper', '.footer-container',
                '[role="contentinfo"]', '.footer-section', '.bottom-footer'
            ],
            'keywords': ['版权所有', '©', 'copyright', '联系我们', '友情链接']
        },
        'header': {
            'name': '页头',
            'selectors': [
                'header', '.header', '#header', '.site-header', '.page-header',
                '.header-content', '.header-wrapper', '.header-container',
                '.top-header', '.main-header'
            ],
            'keywords': []
        },
        'navigation': {
            'name': '导航栏',
            'selectors': [
                'nav', '.nav', '.navigation', '.navbar', '.menu', '.sidebar',
                '[role="navigation"]', '.nav-menu', '.main-nav', '.site-nav',
                '.primary-nav', '.header-nav', '.top-nav', '.side-nav',
                '.navigation-menu', '.breadcrumb', '.breadcrumbs'
            ],
            'keywords': []
        },
        'ads': {
            'name': '广告',
            'selectors': [
                '.ad', '.ads', '.advertisement', '.advert', '.banner',
                '.google-ad', '.adsense', '.ad-container', '.ad-wrapper',
                '.sponsored', '.promotion', '.promo', '[id*="ad"]',
                '[class*="ad-"]', '[class*="ads-"]'
            ],
            'keywords': ['广告', '推广', 'AD', 'ads', 'advertisement', 'sponsored']
        },
        'social': {
            'name': '社交媒体',
            'selectors': [
                '.social', '.social-media', '.social-links', '.share',
                '.share-buttons', '.social-share', '.follow-us',
                '.social-icons', '.social-bar'
            ],
            'keywords': ['分享', '关注我们', 'follow us', 'share']
        },
        'comments': {
            'name': '评论区',
            'selectors': [
                '.comments', '.comment', '.comment-section', '.discussion',
                '.replies', '.feedback', '#comments', '#disqus_thread',
                '.comment-form', '.comment-list'
            ],
            'keywords': ['评论', '留言', 'comments', 'discussion']
        },
        'sidebar': {
            'name': '侧边栏',
            'selectors': [
                '.sidebar', '.side-bar', '.widget', '.widgets',
                '.sidebar-content', '.secondary', '.aside',
                '[role="complementary"]'
            ],
            'keywords': []
        },
        'popup': {
            'name': '弹窗',
            'selectors': [
                '.popup', '.modal', '.overlay', '.lightbox',
                '.dialog', '.alert', '.notification', '.toast',
                '.popup-content', '.modal-content'
            ],
            'keywords': []
        }
    }
    
    def __init__(self, enabled_filters: Optional[List[str]] = None, 
                 custom_selectors: Optional[List[str]] = None,
                 custom_keywords: Optional[List[str]] = None):
        """
        初始化内容过滤器
        
        Args:
            enabled_filters: 启用的预设过滤器列表
            custom_selectors: 自定义CSS选择器列表
            custom_keywords: 自定义关键词列表
        """
        self.enabled_filters = enabled_filters or []
        self.custom_selectors = custom_selectors or []
        self.custom_keywords = custom_keywords or []
        
        # 编译所有过滤规则
        self.compiled_selectors = self._compile_selectors()
        self.compiled_keywords = self._compile_keywords()
        
        logger.info(f"内容过滤器初始化完成，启用过滤器: {self.enabled_filters}")
    
    def _compile_selectors(self) -> List[str]:
        """编译所有CSS选择器"""
        selectors = []
        
        # 添加预设过滤器的选择器
        for filter_name in self.enabled_filters:
            if filter_name in self.PRESET_FILTERS:
                selectors.extend(self.PRESET_FILTERS[filter_name]['selectors'])
        
        # 添加自定义选择器
        selectors.extend(self.custom_selectors)
        
        # 去重
        return list(set(selectors))
    
    def _compile_keywords(self) -> List[str]:
        """编译所有关键词"""
        keywords = []
        
        # 添加预设过滤器的关键词
        for filter_name in self.enabled_filters:
            if filter_name in self.PRESET_FILTERS:
                keywords.extend(self.PRESET_FILTERS[filter_name]['keywords'])
        
        # 添加自定义关键词
        keywords.extend(self.custom_keywords)
        
        # 去重
        return list(set(keywords))
    
    def filter_html(self, html_content: str) -> str:
        """
        过滤HTML内容
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            过滤后的HTML内容
        """
        if not html_content:
            return html_content
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            removed_count = 0
            
            # 使用CSS选择器过滤
            for selector in self.compiled_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        element.decompose()
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"CSS选择器 '{selector}' 执行失败: {str(e)}")
            
            # 使用关键词过滤
            if self.compiled_keywords:
                removed_count += self._filter_by_keywords(soup)
            
            if removed_count > 0:
                logger.info(f"已过滤 {removed_count} 个不需要的元素")
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"HTML过滤失败: {str(e)}")
            return html_content
    
    def _filter_by_keywords(self, soup: BeautifulSoup) -> int:
        """根据关键词过滤内容"""
        removed_count = 0
        
        # 查找包含关键词的元素
        for keyword in self.compiled_keywords:
            # 查找文本内容包含关键词的元素
            elements = soup.find_all(text=re.compile(keyword, re.IGNORECASE))
            for element in elements:
                parent = element.parent
                if parent and parent.name:
                    # 检查父元素是否应该被移除
                    if self._should_remove_by_keyword(parent, keyword):
                        parent.decompose()
                        removed_count += 1
        
        return removed_count
    
    def _should_remove_by_keyword(self, element: Tag, keyword: str) -> bool:
        """判断元素是否应该根据关键词被移除"""
        # 获取元素的文本内容
        text = element.get_text().strip()
        
        # 如果元素文本很短且包含关键词，可能是需要过滤的内容
        if len(text) < 200 and keyword.lower() in text.lower():
            return True
        
        # 检查元素的类名和ID
        class_list = element.get('class', [])
        class_names = ' '.join(class_list) if class_list else ''
        element_id = element.get('id') or ''
        
        if keyword.lower() in class_names.lower() or keyword.lower() in element_id.lower():
            return True
        
        return False
    
    def filter_text(self, text_content: str) -> str:
        """
        过滤纯文本内容
        
        Args:
            text_content: 原始文本内容
            
        Returns:
            过滤后的文本内容
        """
        if not text_content or not self.compiled_keywords:
            return text_content
        
        lines = text_content.split('\n')
        filtered_lines = []
        
        for line in lines:
            should_keep = True
            for keyword in self.compiled_keywords:
                if keyword.lower() in line.lower():
                    # 如果行很短且包含关键词，可能需要过滤
                    if len(line.strip()) < 100:
                        should_keep = False
                        break
            
            if should_keep:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def get_filter_stats(self) -> Dict:
        """获取过滤器统计信息"""
        return {
            'enabled_filters': self.enabled_filters,
            'total_selectors': len(self.compiled_selectors),
            'total_keywords': len(self.compiled_keywords),
            'preset_filters_available': list(self.PRESET_FILTERS.keys())
        }
    
    @classmethod
    def get_preset_filters(cls) -> Dict:
        """获取所有预设过滤器"""
        return cls.PRESET_FILTERS
    
    @classmethod
    def create_from_config(cls, config: Dict) -> 'ContentFilter':
        """从配置字典创建过滤器实例"""
        return cls(
            enabled_filters=config.get('enabled_filters', []),
            custom_selectors=config.get('custom_selectors', []),
            custom_keywords=config.get('custom_keywords', [])
        )


def create_default_filter() -> ContentFilter:
    """创建默认的内容过滤器"""
    return ContentFilter(
        enabled_filters=['footer', 'ads', 'popup'],
        custom_selectors=[],
        custom_keywords=[]
    )


if __name__ == "__main__":
    # 测试代码
    html_test = """
    <html>
    <body>
        <header>页头内容</header>
        <main>
            <h1>主要内容</h1>
            <p>这是页面的主要内容。</p>
        </main>
        <footer>
            <p>版权所有 © 2025</p>
            <p>联系我们</p>
        </footer>
        <div class="ad">广告内容</div>
    </body>
    </html>
    """
    
    # 创建过滤器
    content_filter = ContentFilter(enabled_filters=['footer', 'ads'])
    
    # 过滤HTML
    filtered_html = content_filter.filter_html(html_test)
    print("过滤后的HTML:")
    print(filtered_html)
    
    # 获取统计信息
    stats = content_filter.get_filter_stats()
    print("\n过滤器统计:")
    print(stats) 