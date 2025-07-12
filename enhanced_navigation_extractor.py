#!/usr/bin/env python3
"""
增强的导航栏提取器
专门用于准确提取网站导航栏结构，确保与原始页面完全一致
"""

import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class EnhancedNavigationExtractor:
    """增强的导航栏提取器"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        
        # 导航栏选择器优先级列表（从高到低）
        self.nav_selectors = [
            'nav[role="navigation"]',
            'nav.main-nav',
            'nav.primary-nav',
            'nav.site-nav',
            'nav.header-nav',
            'nav.top-nav',
            '.navbar',
            '.navigation',
            '.nav-menu',
            '.main-navigation',
            '.site-navigation',
            '.header-navigation',
            '.primary-navigation',
            'nav',
            '.nav',
            '.menu',
            '[role="navigation"]',
            '.sidebar-nav',
            '.side-nav'
        ]
    
    def extract_navigation_from_html(self, html_content: str, page_url: str) -> Dict[str, Any]:
        """从HTML内容中提取导航栏"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        navigation_data = {
            'found_navigations': [],
            'primary_navigation': None,
            'all_nav_links': [],
            'navigation_structure': []
        }
        
        # 尝试每个选择器
        for selector in self.nav_selectors:
            nav_elements = soup.select(selector)
            
            for i, nav_element in enumerate(nav_elements):
                nav_info = self._extract_nav_element_info(nav_element, page_url, selector)
                if nav_info['links']:  # 只有包含链接的导航才被认为是有效的
                    navigation_data['found_navigations'].append(nav_info)
                    
                    # 第一个有效的导航作为主导航
                    if navigation_data['primary_navigation'] is None:
                        navigation_data['primary_navigation'] = nav_info
        
        # 收集所有导航链接
        all_links = []
        for nav in navigation_data['found_navigations']:
            all_links.extend(nav['links'])
        
        # 去重
        unique_links = self._deduplicate_links(all_links)
        navigation_data['all_nav_links'] = unique_links
        
        # 构建导航结构
        navigation_data['navigation_structure'] = self._build_navigation_structure(unique_links)
        
        return navigation_data
    
    def _extract_nav_element_info(self, nav_element, page_url: str, selector: str) -> Dict[str, Any]:
        """提取单个导航元素的信息"""
        nav_info = {
            'selector': selector,
            'html': str(nav_element),
            'text': nav_element.get_text(strip=True),
            'links': [],
            'structure': 'flat'  # flat, hierarchical
        }
        
        # 提取所有链接
        links = nav_element.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and text:
                full_url = urljoin(page_url, href)
                if self._is_valid_internal_url(full_url):
                    link_info = {
                        'text': text,
                        'url': full_url,
                        'href': href,
                        'level': self._calculate_link_level(link, nav_element),
                        'parent_text': self._get_parent_text(link),
                        'css_classes': link.get('class', []),
                        'attributes': dict(link.attrs)
                    }
                    nav_info['links'].append(link_info)
        
        # 检测导航结构类型
        if self._has_nested_structure(nav_element):
            nav_info['structure'] = 'hierarchical'
        
        return nav_info
    
    def _calculate_link_level(self, link_element, nav_element) -> int:
        """计算链接的层级"""
        level = 0
        current = link_element.parent
        
        while current and current != nav_element:
            if current.name in ['ul', 'ol', 'li', 'div'] and 'menu' in str(current.get('class', [])).lower():
                level += 1
            current = current.parent
        
        return level
    
    def _get_parent_text(self, link_element) -> Optional[str]:
        """获取链接的父级文本"""
        parent = link_element.parent
        while parent:
            if parent.name in ['li', 'div'] and parent.get_text(strip=True) != link_element.get_text(strip=True):
                # 找到包含当前链接文本的父级元素
                parent_text = parent.get_text(strip=True)
                link_text = link_element.get_text(strip=True)
                if link_text in parent_text:
                    return parent_text.replace(link_text, '').strip()
            parent = parent.parent
        return None
    
    def _has_nested_structure(self, nav_element) -> bool:
        """检测是否有嵌套结构"""
        nested_elements = nav_element.select('ul ul, ol ol, li li, .dropdown, .submenu, .sub-menu')
        return len(nested_elements) > 0
    
    def _is_valid_internal_url(self, url: str) -> bool:
        """检查是否为有效的内部URL"""
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc == self.domain and
                parsed.scheme in ['http', 'https'] and
                not any(ext in url.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js', '.ico'])
            )
        except:
            return False
    
    def _deduplicate_links(self, links: List[Dict]) -> List[Dict]:
        """去重链接"""
        unique_links = []
        seen = set()
        
        for link in links:
            key = f"{link['text']}|{link['url']}"
            if key not in seen:
                seen.add(key)
                unique_links.append(link)
        
        return unique_links
    
    def _build_navigation_structure(self, links: List[Dict]) -> List[Dict]:
        """构建导航结构"""
        structure = []
        
        # 按层级分组
        levels = {}
        for link in links:
            level = link.get('level', 0)
            if level not in levels:
                levels[level] = []
            levels[level].append(link)
        
        # 构建层级结构
        for level in sorted(levels.keys()):
            for link in levels[level]:
                structure_item = {
                    'text': link['text'],
                    'url': link['url'],
                    'level': level,
                    'parent_text': link.get('parent_text'),
                    'type': 'navigation'
                }
                structure.append(structure_item)
        
        return structure
    
    def extract_navigation_from_crawl_result(self, crawl_result: Dict) -> Dict[str, Any]:
        """从爬取结果中提取导航栏"""
        navigation_data = {
            'url': crawl_result.get('url'),
            'extracted_navigation': None,
            'enhanced_navigation': None
        }
        
        # 从已提取的内容中获取导航
        extracted_content = crawl_result.get('extracted_content', {})
        if isinstance(extracted_content, list) and len(extracted_content) > 0:
            extracted_content = extracted_content[0]
        
        if isinstance(extracted_content, dict):
            nav_html = extracted_content.get('navigation', '')
            if nav_html:
                navigation_data['extracted_navigation'] = nav_html
        
        # 从完整HTML中提取增强的导航
        cleaned_html = crawl_result.get('cleaned_html', '')
        if cleaned_html:
            enhanced_nav = self.extract_navigation_from_html(cleaned_html, crawl_result.get('url'))
            navigation_data['enhanced_navigation'] = enhanced_nav
        
        return navigation_data
    
    def compare_navigations(self, original_nav: Dict, extracted_nav: Dict) -> Dict[str, Any]:
        """比较原始导航和提取的导航"""
        comparison = {
            'match_score': 0.0,
            'missing_links': [],
            'extra_links': [],
            'differences': []
        }
        
        # 这里可以实现详细的比较逻辑
        # 比较链接数量、文本、URL等
        
        return comparison


def enhance_navigation_extraction(crawl_results: List[Dict], base_url: str) -> Dict[str, Any]:
    """增强导航栏提取的主函数"""
    extractor = EnhancedNavigationExtractor(base_url)
    
    enhanced_results = {
        'base_url': base_url,
        'total_pages': len(crawl_results),
        'pages_with_navigation': 0,
        'unique_navigation_links': [],
        'navigation_structure': [],
        'page_navigations': []
    }
    
    all_nav_links = []
    
    for result in crawl_results:
        page_nav = extractor.extract_navigation_from_crawl_result(result)
        enhanced_results['page_navigations'].append(page_nav)
        
        if page_nav['enhanced_navigation'] and page_nav['enhanced_navigation']['all_nav_links']:
            enhanced_results['pages_with_navigation'] += 1
            all_nav_links.extend(page_nav['enhanced_navigation']['all_nav_links'])
    
    # 去重所有导航链接
    unique_links = extractor._deduplicate_links(all_nav_links)
    enhanced_results['unique_navigation_links'] = unique_links
    
    # 构建全局导航结构
    enhanced_results['navigation_structure'] = extractor._build_navigation_structure(unique_links)
    
    return enhanced_results


if __name__ == "__main__":
    # 示例用法
    base_url = "https://docs.cursor.com"
    
    # 假设我们有一些爬取结果
    sample_results = [
        {
            'url': 'https://docs.cursor.com/welcome',
            'title': 'Welcome',
            'cleaned_html': '<nav><a href="/get-started">Get Started</a><a href="/models">Models</a></nav>',
            'extracted_content': [{'navigation': '<nav><a href="/get-started">Get Started</a></nav>'}]
        }
    ]
    
    enhanced = enhance_navigation_extraction(sample_results, base_url)
    print(json.dumps(enhanced, indent=2, ensure_ascii=False)) 