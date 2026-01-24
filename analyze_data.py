import pymysql
import datetime
from collections import Counter

# MySQL数据库配置
MYSQL_CONFIG = {
    'host': '121.41.230.15',
    'user': 'root',
    'password': '0595',
    'database': 'allStarLink',
    'charset': 'utf8',
    'cursorclass': pymysql.cursors.DictCursor
}

def analyze():
    print("正在连接数据库进行数据分析...")
    try:
        connection = pymysql.connect(**MYSQL_CONFIG)
        with connection.cursor() as cursor:
            # 1. 总节点数
            cursor.execute("SELECT COUNT(*) as count FROM nodes")
            total_nodes = cursor.fetchone()['count']
            
            # 2. 活跃节点数 (is_active=1)
            cursor.execute("SELECT COUNT(*) as count FROM nodes WHERE is_active=1")
            active_nodes = cursor.fetchone()['count']
            
            # 3. Top 10 拥有者 (Owner)
            cursor.execute("SELECT owner, COUNT(*) as count FROM nodes GROUP BY owner ORDER BY count DESC LIMIT 10")
            top_owners = cursor.fetchall()
            
            # 4. 节点频率分布 (简单统计)
            cursor.execute("SELECT frequency, COUNT(*) as count FROM nodes GROUP BY frequency ORDER BY count DESC LIMIT 10")
            top_freqs = cursor.fetchall()

            print("\n" + "="*30)
            print("📊 AllStarLink 数据分析报告")
            print("="*30)
            print(f"总节点数: {total_nodes}")
            print(f"活跃节点数 (有经纬度): {active_nodes} ({active_nodes/total_nodes*100:.2f}%)")
            print("-" * 30)
            
            print("🏆 Top 10 节点拥有者:")
            for i, row in enumerate(top_owners):
                print(f"  {i+1}. {row['owner']}: {row['count']} 个节点")
            print("-" * 30)
            
            print("📡 最常见的频率:")
            for i, row in enumerate(top_freqs):
                freq = row['frequency']
                if not freq: freq = "Unknown"
                print(f"  {i+1}. {freq}: {row['count']} 个节点")
                
    except Exception as e:
        print(f"分析出错: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    analyze()
