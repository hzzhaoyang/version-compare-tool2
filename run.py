#!/usr/bin/env python3
"""
版本比较工具启动脚本 - FastAPI版本
"""
import sys
import os
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    try:
        print("🚀 正在启动版本比较工具 (FastAPI版)...")
        
        port = int(os.getenv('PORT', 9112))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        print(f"📡 服务将在端口 {port} 启动")
        print(f"🔧 调试模式: {'开启' if debug else '关闭'}")
        print(f"📖 API文档: http://localhost:{port}/docs")
        print("=" * 50)
        
        # 使用uvicorn启动FastAPI应用
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=port,
            reload=debug,
            log_level="info" if not debug else "debug"
        )
        
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 