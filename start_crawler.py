#!/usr/bin/env python3
"""
智能网站爬虫 - 集成启动脚本
支持增强导航功能的统一启动入口
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional

def check_dependencies():
    """检查依赖是否安装"""
    required_packages = [
        ('crawl4ai', 'crawl4ai'),
        ('beautifulsoup4', 'bs4'),
        ('flask', 'flask'),
        ('flask-cors', 'flask_cors'),
        ('flask-socketio', 'flask_socketio')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        
        print("\n📦 请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        print("\n或者单独安装:")
        print("pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_enhanced_navigation():
    """检查增强导航功能状态"""
    enhanced_nav_file = Path("enhanced_navigation_extractor.py")
    
    if enhanced_nav_file.exists():
        try:
            # 尝试导入测试
            from enhanced_navigation_extractor import EnhancedNavigationExtractor
            print("✅ 增强导航功能可用")
            return True
        except Exception as e:
            print(f"❌ 增强导航功能导入失败: {e}")
            return False
    else:
        print("⚠️  增强导航功能不可用 - 文件不存在")
        return False

def display_startup_info():
    """显示启动信息"""
    print("🚀 智能网站爬虫 - 集成启动脚本")
    print("=" * 50)
    
    # 检查依赖
    print("\n📦 检查依赖...")
    deps_ok = check_dependencies()
    
    # 检查增强导航功能
    print("\n🔍 检查增强导航功能...")
    enhanced_nav_ok = check_enhanced_navigation()
    
    if enhanced_nav_ok:
        print("\n🎯 增强导航功能特性:")
        print("   • 15种专业导航选择器（vs 原来的3种）")
        print("   • 完整HTML结构保留（vs 原来的纯文本）")
        print("   • 多层级导航识别")
        print("   • 智能链接提取和去重")
        print("   • 导航结构分析和报告")
        print("   • 与现有系统完全兼容")
    
    print("\n" + "=" * 50)
    
    return deps_ok, enhanced_nav_ok

def start_web_server():
    """启动Web服务器"""
    print("🌐 启动Web服务器...")
    
    # 检查Web目录和启动脚本
    web_dir = Path("web")
    start_script = web_dir / "start.py"
    
    if not web_dir.exists():
        print("❌ Web目录不存在")
        return False
    
    if not start_script.exists():
        print("❌ Web服务器启动脚本不存在")
        print("   请确保 web/start.py 文件存在")
        return False
    
    try:
        # 使用subprocess运行Web服务器
        import subprocess
        
        # 切换到Web目录并运行启动脚本
        result = subprocess.run([
            sys.executable, "start.py"
        ], cwd=str(web_dir), capture_output=False)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Web服务器启动失败: {e}")
        print("\n🔧 故障排除:")
        print("   1. 确保所有依赖已安装: pip install -r requirements.txt")
        print("   2. 检查端口5000是否被占用")
        print("   3. 确保web/start.py文件存在且无语法错误")
        return False

def start_command_line(url: str, output_dir: Optional[str] = None):
    """启动命令行版本"""
    print(f"💻 启动命令行版本...")
    print(f"🌐 目标URL: {url}")
    
    # 导入并运行爬虫
    try:
        import asyncio
        
        # 确保当前目录在Python路径中
        current_dir = str(Path.cwd())
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from website_crawler import WebsiteCrawler
        
        # 创建爬虫实例
        output_dir = output_dir or f"crawl_results_{Path(url).name}"
        crawler = WebsiteCrawler(url, output_dir)
        
        # 运行爬虫
        async def run_crawler():
            try:
                # 发现网站结构
                discovered_urls = await crawler.discover_website_structure(
                    max_depth=3,
                    max_pages=50
                )
                
                # 抓取所有内容
                results = await crawler.crawl_all_content(
                    discovered_urls,
                    batch_size=5
                )
                
                print(f"\n📊 抓取完成:")
                print(f"  ✅ 成功抓取: {results['successful_crawls']} 个页面")
                print(f"  ❌ 失败页面: {results['failed_crawls']} 个页面")
                print(f"  📁 输出目录: {results['output_directory']}")
                
                return True
                
            except Exception as e:
                print(f"❌ 爬虫执行失败: {str(e)}")
                return False
        
        # 运行异步函数
        success = asyncio.run(run_crawler())
        return success
        
    except Exception as e:
        print(f"❌ 命令行版本启动失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="智能网站爬虫 - 集成启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python start_crawler.py web                    # 启动Web界面
  python start_crawler.py cli https://example.com  # 命令行模式
  python start_crawler.py cli https://example.com --output my_results  # 指定输出目录
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['web', 'cli'],
        help='启动模式: web (Web界面) 或 cli (命令行)'
    )
    
    parser.add_argument(
        'url',
        nargs='?',
        help='目标网站URL (命令行模式必需)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出目录 (仅命令行模式)'
    )
    
    args = parser.parse_args()
    
    # 显示启动信息
    deps_ok, enhanced_nav_ok = display_startup_info()
    
    if not deps_ok:
        print("\n❌ 依赖检查失败，请先安装必要的依赖包")
        sys.exit(1)
    
    # 根据模式启动
    if args.mode == 'web':
        print("\n🌐 启动Web界面模式...")
        success = start_web_server()
    elif args.mode == 'cli':
        if not args.url:
            print("❌ 命令行模式需要提供目标URL")
            parser.print_help()
            sys.exit(1)
        
        print("\n💻 启动命令行模式...")
        success = start_command_line(args.url, args.output)
    else:
        parser.print_help()
        sys.exit(1)
    
    if success:
        print("\n✅ 程序执行完成")
    else:
        print("\n❌ 程序执行失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 