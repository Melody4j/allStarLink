#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink 准实时ETL启动脚本
提供友好的交互式启动界面
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from scraperV1.realtime_etl_config import get_config_summary, get_database_url
except ImportError:
    print("警告: 无法导入配置文件，使用默认配置")

def print_banner():
    """打印启动横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                   AllStarLink 准实时ETL爬虫                    ║
║                Real-time ETL Scraper v1.0                    ║
╠═══════════════════════════════════════════════════════════════╣
║  功能特性:                                                     ║
║  • 每分钟自动爬取节点数据                                       ║
║  • 内存状态缓存和异动检测                                       ║
║  • 向量化数据处理 (支持2万+节点)                               ║
║  • 按需写入DWD和DIM表                                          ║
║  • 可配置ODS快照间隔                                           ║
║  • 异常安全保护机制                                             ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_config_info():
    """显示配置信息"""
    try:
        config = get_config_summary()
        print("\n📊 当前配置信息:")
        print("─" * 50)
        print(f"数据库地址: {config['database']['host']}")
        print(f"数据库名称: {config['database']['database']}")
        print(f"用户名: {config['database']['user']}")
        print(f"地理位移阈值: {config['etl']['geo_threshold']} 度")
        print(f"批处理大小: {config['etl']['batch_size']} 条")
        print(f"默认ODS间隔: {config['etl']['default_ods_interval']} 分钟")
        print(f"ODS表: {config['tables']['ods_table']}")
        print(f"DWD表: {config['tables']['dwd_table']}")
        print(f"DIM表: {config['tables']['dim_table']}")
        print("─" * 50)
    except Exception as e:
        print(f"⚠️  配置信息获取失败: {e}")

def interactive_mode():
    """交互式模式选择"""
    print("\n🚀 请选择运行模式:")
    print("1. 单次执行 (测试用)")
    print("2. 准实时循环 (推荐)")
    print("3. 自定义配置")
    print("4. 显示帮助")
    print("5. 退出")

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == '1':
        return run_single_mode()
    elif choice == '2':
        return run_realtime_mode()
    elif choice == '3':
        return run_custom_mode()
    elif choice == '4':
        return show_help()
    elif choice == '5':
        print("👋 再见!")
        return True
    else:
        print("❌ 无效选项，请重新选择")
        return False

def run_single_mode():
    """运行单次模式"""
    print("\n🔄 启动单次ETL执行...")
    cmd = [sys.executable, "allstarlink_realtime_etl.py", "--mode", "single"]
    return run_command(cmd)

def run_realtime_mode():
    """运行准实时模式"""
    print("\n⏰ ODS快照写入间隔配置:")
    print("1. 30分钟 (高频)")
    print("2. 60分钟 (默认)")
    print("3. 120分钟 (低频)")
    print("4. 自定义")

    interval_choice = input("请选择间隔 (1-4): ").strip()

    interval_map = {
        '1': 30,
        '2': 60,
        '3': 120
    }

    if interval_choice in interval_map:
        interval = interval_map[interval_choice]
    elif interval_choice == '4':
        try:
            interval = int(input("请输入自定义间隔(分钟): "))
            if interval <= 0:
                print("❌ 间隔必须大于0")
                return False
        except ValueError:
            print("❌ 无效数字")
            return False
    else:
        print("❌ 无效选项")
        return False

    print(f"\n🚀 启动准实时ETL (ODS间隔: {interval}分钟)...")
    print("💡 提示: 按Ctrl+C可以优雅停止")
    cmd = [sys.executable, "allstarlink_realtime_etl.py",
           "--mode", "realtime", "--ods-interval", str(interval)]
    return run_command(cmd)

def run_custom_mode():
    """自定义配置模式"""
    print("\n⚙️  自定义配置模式")

    mode = input("运行模式 (single/realtime) [realtime]: ").strip() or "realtime"
    if mode not in ['single', 'realtime']:
        print("❌ 无效模式")
        return False

    cmd = [sys.executable, "allstarlink_realtime_etl.py", "--mode", mode]

    if mode == 'realtime':
        try:
            interval = input("ODS间隔(分钟) [60]: ").strip()
            if interval:
                interval = int(interval)
                cmd.extend(["--ods-interval", str(interval)])
        except ValueError:
            print("❌ 无效间隔，使用默认值")

    print(f"\n🚀 启动自定义配置: {' '.join(cmd[1:])}")
    return run_command(cmd)

def show_help():
    """显示帮助信息"""
    print("\n📖 帮助信息")
    print("─" * 60)
    print("命令行用法:")
    print("  python allstarlink_realtime_etl.py --mode single")
    print("  python allstarlink_realtime_etl.py --mode realtime --ods-interval 30")
    print()
    print("参数说明:")
    print("  --mode: 运行模式 (single/realtime)")
    print("  --ods-interval: ODS快照间隔，单位分钟 (仅realtime模式)")
    print()
    print("文件说明:")
    print("  allstarlink_realtime_etl.py    - 主程序")
    print("  realtime_etl_config.py         - 配置文件")
    print("  README_REALTIME_ETL.md         - 详细文档")
    print()
    print("数据库表:")
    print("  ods_asl_nodes_snapshot  - ODS快照表")
    print("  dwd_node_events_fact    - DWD事件表")
    print("  dim_nodes              - DIM维度表")
    print("─" * 60)

    input("\n按回车键返回主菜单...")
    return False

def run_command(cmd):
    """执行命令"""
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断操作")
        return True
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        return False

def check_dependencies():
    """检查依赖项"""
    required_modules = ['pandas', 'numpy', 'sqlalchemy', 'pymysql', 'requests']
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print("❌ 缺少必需的Python模块:")
        for module in missing_modules:
            print(f"   • {module}")
        print("\n请运行以下命令安装依赖:")
        print(f"   pip install {' '.join(missing_modules)}")
        return False

    return True

def check_files():
    """检查必需文件"""
    required_files = ['allstarlink_realtime_etl.py', 'realtime_etl_config.py']
    missing_files = []

    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)

    if missing_files:
        print("❌ 缺少必需文件:")
        for file in missing_files:
            print(f"   • {file}")
        return False

    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AllStarLink准实时ETL启动器')
    parser.add_argument('--non-interactive', action='store_true',
                       help='非交互模式，直接启动默认配置')
    parser.add_argument('--mode', choices=['single', 'realtime'], default='realtime',
                       help='运行模式')
    parser.add_argument('--ods-interval', type=int, default=60,
                       help='ODS间隔(分钟)')

    args = parser.parse_args()

    print_banner()

    # 检查环境
    if not check_dependencies():
        sys.exit(1)

    if not check_files():
        sys.exit(1)

    print_config_info()

    if args.non_interactive:
        # 非交互模式
        print(f"\n🚀 非交互模式启动: {args.mode}")
        cmd = [sys.executable, "allstarlink_realtime_etl.py", "--mode", args.mode]
        if args.mode == 'realtime':
            cmd.extend(["--ods-interval", str(args.ods_interval)])
        success = run_command(cmd)
        sys.exit(0 if success else 1)
    else:
        # 交互模式
        while True:
            try:
                if interactive_mode():
                    break
            except KeyboardInterrupt:
                print("\n\n👋 再见!")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                break

if __name__ == "__main__":
    main()