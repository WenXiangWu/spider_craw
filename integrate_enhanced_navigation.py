#!/usr/bin/env python3
"""
集成增强导航栏提取器
将增强的导航栏提取功能集成到现有的爬虫系统中
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import logging

# 尝试导入增强导航提取器
try:
    from enhanced_navigation_extractor import EnhancedNavigationExtractor, enhance_navigation_extraction
except ImportError:
    print("警告: 无法导入增强导航提取器，请确保 enhanced_navigation_extractor.py 文件存在")
    EnhancedNavigationExtractor = None

logger = logging.getLogger(__name__)


def integrate_enhanced_navigation_to_server():
    """将增强导航功能集成到服务器代码中"""
    
    server_file = Path("web/server.py")
    if not server_file.exists():
        print("错误: 找不到 web/server.py 文件")
        return False
    
    # 读取服务器代码
    with open(server_file, 'r', encoding='utf-8') as f:
        server_content = f.read()
    
    # 检查是否已经集成
    if "EnhancedNavigationExtractor" in server_content:
        print("增强导航功能已经集成到服务器中")
        return True
    
    # 在文件顶部添加导入
    import_line = """
# 增强导航栏提取器
try:
    from enhanced_navigation_extractor import EnhancedNavigationExtractor
    ENHANCED_NAV_AVAILABLE = True
except ImportError:
    ENHANCED_NAV_AVAILABLE = False
    print("警告: 增强导航栏提取器不可用")
"""
    
    # 在导入部分后添加
    lines = server_content.split('\n')
    insert_index = -1
    
    for i, line in enumerate(lines):
        if line.startswith('logger = logging.getLogger(__name__)'):
            insert_index = i + 1
            break
    
    if insert_index > 0:
        lines.insert(insert_index, import_line)
        
        # 保存修改后的文件
        with open(server_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print("✅ 成功集成增强导航功能到服务器")
        return True
    else:
        print("❌ 无法找到合适的位置插入代码")
        return False


def enhance_existing_crawl_results(results_dir: str = "crawl_results") -> Dict[str, Any]:
    """增强现有的爬取结果"""
    
    results_path = Path(results_dir)
    if not results_path.exists():
        print(f"错误: 结果目录 {results_dir} 不存在")
        return {}
    
    # 查找爬取结果文件
    content_dir = results_path / "content"
    if not content_dir.exists():
        print(f"错误: 内容目录 {content_dir} 不存在")
        return {}
    
    # 读取所有爬取结果
    crawl_results = []
    for json_file in content_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
                crawl_results.append(result)
        except Exception as e:
            print(f"警告: 无法读取文件 {json_file}: {e}")
    
    if not crawl_results:
        print("没有找到有效的爬取结果")
        return {}
    
    # 获取基础URL
    base_url = crawl_results[0].get('url', '').split('/')[0:3]
    if len(base_url) == 3:
        base_url = '/'.join(base_url)
    else:
        print("警告: 无法确定基础URL")
        base_url = "https://example.com"
    
    print(f"📊 处理 {len(crawl_results)} 个爬取结果...")
    print(f"🌐 基础URL: {base_url}")
    
    # 使用增强导航提取器
    if EnhancedNavigationExtractor:
        enhanced_results = enhance_navigation_extraction(crawl_results, base_url)
        
        # 保存增强结果
        enhanced_file = results_path / "enhanced_navigation.json"
        with open(enhanced_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 增强导航结果已保存到: {enhanced_file}")
        
        # 生成导航报告
        generate_navigation_report(enhanced_results, results_path)
        
        return enhanced_results
    else:
        print("❌ 增强导航提取器不可用")
        return {}


def generate_navigation_report(enhanced_results: Dict[str, Any], output_dir: Path):
    """生成导航栏分析报告"""
    
    report_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>导航栏分析报告</title>
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
        .comparison {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>导航栏分析报告</h1>
        <p><strong>网站:</strong> {enhanced_results.get('base_url', 'N/A')}</p>
        <p><strong>分析时间:</strong> {enhanced_results.get('analysis_time', 'N/A')}</p>
    </div>
    
    <div class="stats">
        <h3>统计信息</h3>
        <p>总页面数: <strong>{enhanced_results.get('total_pages', 0)}</strong></p>
        <p>包含导航的页面数: <strong>{enhanced_results.get('pages_with_navigation', 0)}</strong></p>
        <p>唯一导航链接数: <strong>{len(enhanced_results.get('unique_navigation_links', []))}</strong></p>
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
    
    <h2>页面导航详情</h2>
    <div class="page-details">
"""
    
    # 添加每个页面的导航详情
    for page_nav in enhanced_results.get('page_navigations', []):
        url = page_nav.get('url', 'N/A')
        enhanced_nav = page_nav.get('enhanced_navigation', {})
        
        if enhanced_nav and enhanced_nav.get('all_nav_links'):
            report_html += f"""
            <div class="page-nav">
                <h4>页面: {url}</h4>
                <p>找到 {len(enhanced_nav.get('all_nav_links', []))} 个导航链接</p>
                <ul>
"""
            for link in enhanced_nav.get('all_nav_links', []):
                report_html += f"""
                    <li><a href="{link.get('url', '#')}" target="_blank">{link.get('text', 'N/A')}</a></li>
"""
            report_html += """
                </ul>
            </div>
"""
    
    report_html += """
    </div>
</body>
</html>
"""
    
    # 保存报告
    report_file = output_dir / "navigation_report.html"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_html)
    
    print(f"📊 导航分析报告已生成: {report_file}")


def main():
    """主函数"""
    print("🚀 开始集成增强导航栏提取功能...")
    
    # 1. 集成到服务器
    print("\n1. 集成到服务器...")
    # integrate_enhanced_navigation_to_server()
    
    # 2. 增强现有结果
    print("\n2. 增强现有爬取结果...")
    results = enhance_existing_crawl_results()
    
    if results:
        print(f"\n✅ 成功处理 {results.get('total_pages', 0)} 个页面")
        print(f"📊 发现 {len(results.get('unique_navigation_links', []))} 个唯一导航链接")
        print(f"🎯 {results.get('pages_with_navigation', 0)} 个页面包含导航栏")
    else:
        print("\n❌ 处理失败")


if __name__ == "__main__":
    main() 