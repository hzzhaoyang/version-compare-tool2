#!/usr/bin/env python3
"""
版本比较工具启动脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.main import app, init_service

if __name__ == '__main__':
    try:
        print("🚀 正在启动版本比较工具...")
        init_service()
        
        port = int(os.getenv('PORT', 10000))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        print(f"📡 服务将在端口 {port} 启动")
        print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
        print("=" * 50)
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
        
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1) 