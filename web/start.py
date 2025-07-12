#!/usr/bin/env python3
"""
智能网站爬虫 Web 版启动脚本
"""

import sys
import subprocess
import os
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    required_packages = [
        'flask',
        'flask_cors', 
        'flask_socketio',
        'crawl4ai',
        'beautifulsoup4'  # 增强导航功能需要
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'flask_cors':
                __import__('flask_cors')
            elif package == 'flask_socketio':
                __import__('flask_socketio')
            elif package == 'beautifulsoup4':
                __import__('bs4')
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        
        print("\n📦 请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        print("\n或者单独安装:")
        print("pip install flask flask-cors flask-socketio crawl4ai beautifulsoup4")
        return False
    
    return True

def check_enhanced_navigation_status():
    """检查增强导航功能状态"""
    print("\n🔍 检查增强导航功能状态...")
    
    # 检查增强导航提取器文件
    enhanced_nav_file = Path("../enhanced_navigation_extractor.py")
    if enhanced_nav_file.exists():
        print("✅ 增强导航提取器文件存在")
        
        # 尝试导入测试
        try:
            sys.path.insert(0, str(enhanced_nav_file.parent))
            from enhanced_navigation_extractor import EnhancedNavigationExtractor
            print("✅ 增强导航提取器可正常导入")
            
            # 测试基本功能
            test_extractor = EnhancedNavigationExtractor("https://example.com")
            print(f"✅ 增强导航提取器初始化成功，支持 {len(test_extractor.nav_selectors)} 种导航选择器")
            
            return True
        except Exception as e:
            print(f"❌ 增强导航提取器导入失败: {e}")
            return False
    else:
        print("❌ 增强导航提取器文件不存在")
        print("   请确保 enhanced_navigation_extractor.py 文件在项目根目录")
        return False

def initialize_enhanced_navigation():
    """初始化增强导航功能"""
    print("\n🚀 初始化增强导航功能...")
    
    # 检查服务器文件是否已集成增强导航
    server_file = Path("server.py")
    if server_file.exists():
        with open(server_file, 'r', encoding='utf-8') as f:
            server_content = f.read()
        
        if "EnhancedNavigationExtractor" in server_content:
            print("✅ 服务器已集成增强导航功能")
        else:
            print("⚠️  服务器尚未集成增强导航功能")
            print("   建议运行 python integrate_enhanced_navigation.py 进行集成")
    
    # 检查配置文件
    config_files = ["app.js", "index.html"]
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✅ 配置文件 {config_file} 存在")
        else:
            print(f"⚠️  配置文件 {config_file} 不存在")

def display_enhanced_features():
    """显示增强功能特性"""
    print("\n🎯 增强导航功能特性:")
    print("   • 15种专业导航选择器（vs 原来的3种）")
    print("   • 完整HTML结构保留（vs 原来的纯文本）")
    print("   • 多层级导航识别")
    print("   • 智能链接提取和去重")
    print("   • 导航结构分析和报告")
    print("   • 与现有系统完全兼容")

def start_server():
    """启动服务器"""
    print("🚀 启动智能网站爬虫 Web 服务器...")
    
    # 检查基础依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查增强导航功能
    enhanced_nav_available = check_enhanced_navigation_status()
    
    if enhanced_nav_available:
        # 初始化增强导航功能
        initialize_enhanced_navigation()
        display_enhanced_features()
        print("\n✨ 增强导航功能已激活！")
    else:
        print("\n⚠️  增强导航功能不可用，将使用基础导航功能")
        print("   要启用增强功能，请参考 README.md 中的导航栏增强功能章节")
    
    # 启动服务器
    try:
        from server import app, socketio
        print("\n🌐 服务器信息:")
        print("📱 Web界面: http://localhost:5000")
        print("🔌 API接口: http://localhost:5000/api/tasks")
        print("📊 导航增强: " + ("✅ 已启用" if enhanced_nav_available else "❌ 未启用"))
        print("💡 提示: 按 Ctrl+C 停止服务器")
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 故障排除:")
        print("   1. 确保所有依赖已安装: pip install -r requirements.txt")
        print("   2. 检查端口5000是否被占用")
        print("   3. 确保server.py文件存在且无语法错误")
        sys.exit(1)

if __name__ == '__main__':
    start_server() 