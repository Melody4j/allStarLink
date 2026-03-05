
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AllStarLink Neo4j拓扑数据爬虫
实现快照扫描器、优先级调度器和异步工作者的解耦架构
"""

import asyncio
import aiohttp
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from neo4j import AsyncGraphDatabase
import redis.asyncio as redis
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置信息
NEO4J_CONFIG = {
    'uri': 'bolt://121.41.230.15:7687',
    'user': 'neo4j',
    'password': '0595'
}

REDIS_CONFIG = {
    'host': '121.41.230.15',
    'port': 6379,
    'password': '0595',
    'db': 0
}

API_CONFIG = {
    'base_url': 'https://stats.allstarlink.org/api/stats',
    'node_list_url': 'http://stats.allstarlink.org/api/stats/nodeList',
    'rate_limit': 30,  # 每分钟30个请求
    'rate_limit_window': 60,  # 时间窗口60秒
    'max_retries': 3,  # 最大重试次数
    'retry_backoff': 2,  # 指数退避因子
    '429_cooldown': 3600  # HTTP 429冷却时间（秒）
}

# 优先级配置
PRIORITY_CONFIG = {
    'high': 100,    # 连接数 > 5 的 Hub 节点
    'normal': 50,   # 连接数 1-4 的活跃节点
    'low': 10       # 在线但无连接的边缘节点
}


class RedisPriorityQueue:
    """Redis优先级队列管理器"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = 'asl_task_queue'
        self.task_set_key = 'asl_task_set'

    async def clear(self):
        """
        清空队列和任务集合
        """
        try:
            await self.redis.delete(self.queue_key)
            await self.redis.delete(self.task_set_key)
            logger.info("已清空Redis队列和任务集合")
        except Exception as e:
            logger.error(f"清空Redis队列失败: {e}")

    async def enqueue(self, node_id: int, priority: int) -> bool:
        """
        将节点ID加入优先级队列

        Args:
            node_id: 节点ID
            priority: 优先级分数

        Returns:
            bool: 是否成功入队
        """
        try:
            # 使用有序集合实现优先级队列，分数越高优先级越高
            await self.redis.zadd(self.queue_key, {str(node_id): priority})
            # 记录任务集合，用于去重
            await self.redis.sadd(self.task_set_key, str(node_id))
            logger.debug(f"节点 {node_id} 已加入优先级队列，优先级: {priority}")
            return True
        except Exception as e:
            logger.error(f"节点 {node_id} 入队失败: {e}")
            return False

    async def dequeue(self) -> Optional[int]:
        """
        从优先级队列中取出最高优先级的节点ID

        Returns:
            Optional[int]: 节点ID，如果队列为空则返回None
        """
        try:
            # 从有序集合中取出分数最高的元素
            result = await self.redis.zpopmax(self.queue_key)
            if result:
                node_id = int(result[0][0])
                # 从任务集合中移除
                await self.redis.srem(self.task_set_key, str(node_id))
                logger.debug(f"从队列中取出节点 {node_id}")
                return node_id
            return None
        except Exception as e:
            logger.error(f"从队列中取出节点失败: {e}")
            return None

    async def get_queue_size(self) -> int:
        """
        获取队列大小

        Returns:
            int: 队列中的任务数量
        """
        try:
            return await self.redis.zcard(self.queue_key)
        except Exception as e:
            logger.error(f"获取队列大小失败: {e}")
            return 0

    async def remove_node(self, node_id: int) -> bool:
        """
        从队列中移除指定节点

        Args:
            node_id: 要移除的节点ID

        Returns:
            bool: 是否成功移除
        """
        try:
            await self.redis.zrem(self.queue_key, str(node_id))
            await self.redis.srem(self.task_set_key, str(node_id))
            logger.debug(f"从队列中移除节点 {node_id}")
            return True
        except Exception as e:
            logger.error(f"从队列中移除节点 {node_id} 失败: {e}")
            return False

    async def is_in_queue(self, node_id: int) -> bool:
        """
        检查节点是否在队列中

        Args:
            node_id: 节点ID

        Returns:
            bool: 节点是否在队列中
        """
        try:
            return await self.redis.sismember(self.task_set_key, str(node_id))
        except Exception as e:
            logger.error(f"检查节点 {node_id} 是否在队列中失败: {e}")
            return False


class Neo4jManager:
    """Neo4j数据库管理器"""

    def __init__(self, neo4j_config: Dict):
        self.driver = AsyncGraphDatabase.driver(
            neo4j_config['uri'],
            auth=(neo4j_config['user'], neo4j_config['password'])
        )

    async def close(self):
        """关闭Neo4j连接"""
        await self.driver.close()

    async def initialize_constraints(self):
        """初始化Neo4j数据库约束"""
        async with self.driver.session() as session:
            # 创建节点ID的唯一性约束
            await session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.node_id IS UNIQUE"
            )
            logger.info("Neo4j约束初始化完成")

    async def update_node(self, node_data: Dict):
        """
        更新节点数据到Neo4j

        Args:
            node_data: 节点数据字典
        """
        async with self.driver.session() as session:
            node_id = node_data.get('node_id')
            if not node_id:
                logger.warning("节点数据缺少node_id，跳过更新")
                return

            # 提取节点属性
            properties = {
                'node_id': node_id,
                'callsign': node_data.get('callsign', ''),
                'node_type': node_data.get('node_type', 'Unknown'),
                'lat': float(node_data.get('lat', 0.0)),
                'lon': float(node_data.get('lon', 0.0)),
                'uptime': int(node_data.get('uptime', 0)),
                'total_keyups': int(node_data.get('total_keyups', 0)),
                'total_tx_time': int(node_data.get('total_tx_time', 0)),
                'last_seen': node_data.get('last_seen', datetime.now().isoformat()),
                'active': True,
                'updated_at': datetime.now().isoformat(),
                'source': node_data.get('source', 'allstarlink'),  # 节点来源标识
                'node_rank': node_data.get('node_rank', 'Normal'),  # 节点等级：Normal/Core
                'features': node_data.get('features', []),  # 节点特性列表
                'tone': node_data.get('tone'),  # 技术参数：CTCSS/DCS
                'location_desc': node_data.get('location_desc'),  # 业务信息描述
                'hardware_type': node_data.get('hardware_type', 'Unknown')  # 硬件类型
            }

            # 使用MERGE确保节点存在，然后更新属性
            query = """
            MERGE (n:Node {node_id: $node_id})
            SET n += $properties
            """
            await session.run(query, node_id=node_id, properties=properties)
            logger.debug(f"节点 {node_id} 数据已更新到Neo4j")

    async def update_topology(self, node_id: int, linked_nodes: List[Dict], connection_modes: str):
        """
        更新节点拓扑关系到Neo4j

        Args:
            node_id: 源节点ID
            linked_nodes: 连接的节点列表
            connection_modes: 连接模式字符串，如"T62340,T68245"
        """
        async with self.driver.session() as session:
            current_time = datetime.now().isoformat()

            # 解析连接模式
            connection_dict = self._parse_connection_modes(connection_modes)

            # 处理每个连接的节点
            for linked_node in linked_nodes:
                # 获取目标节点ID
                # name字段是真正的节点ID（无论是AllStarLink节点还是其他电台节点）
                # Node_ID是数据库的自增ID，不是节点ID
                # 节点ID可能是整数或字符串（如'HP104104'）
                target_id = linked_node.get('name')
                if not target_id:
                    continue

                # 直接使用target_id，不强制转换为整数
                # 支持整数和字符串类型的节点ID
                dst_id = target_id if isinstance(target_id, (int, str)) else str(target_id)

                # 获取连接状态和模式
                status = linked_node.get('Status', 'Inactive')
                direction = connection_dict.get(str(dst_id), 'Unknown')

                # 使用MERGE创建或更新关系
                query = """
                MERGE (src:Node {node_id: $src_id})
                MERGE (dst:Node {node_id: $dst_id})
                MERGE (src)-[r:CONNECTED_TO]->(dst)
                SET r.status = $status,
                    r.direction = $direction,
                    r.last_updated = $last_updated,
                    r.active = $active
                """
                await session.run(
                    query,
                    src_id=node_id,
                    dst_id=dst_id,
                    status=status,
                    direction=direction,
                    last_updated=current_time,
                    active=(status == 'Active')
                )

            # 清理失效的关系
            await self._cleanup_stale_relationships(session, node_id, connection_dict, current_time)

    def _parse_connection_modes(self, connection_modes: str) -> Dict[str, str]:
        """
        解析连接模式字符串

        Args:
            connection_modes: 连接模式字符串，如"T62340,T68245"

        Returns:
            Dict[str, str]: 节点ID到连接模式的映射
        """
        connection_dict = {}
        if not connection_modes:
            return connection_dict

        for item in connection_modes.split(','):
            if not item:
                continue

            # 提取前缀和节点ID
            prefix = item[0] if item else ''
            node_id = item[1:] if len(item) > 1 else ''

            if node_id.isdigit():
                connection_dict[node_id] = self._prefix_to_direction(prefix)

        return connection_dict

    def _prefix_to_direction(self, prefix: str) -> str:
        """
        将连接模式前缀转换为方向描述

        Args:
            prefix: 连接模式前缀

        Returns:
            str: 方向描述
        """
        prefix_map = {
            'T': 'Transceive',  # 双向收发
            'R': 'RX Only',     # 仅接收
            'L': 'Local',       # 本地链路
            'P': 'Permanent'    # 永久连接
        }
        return prefix_map.get(prefix, 'Unknown')

    async def _cleanup_stale_relationships(self, session, node_id: int, 
                                          current_connections: Dict[str, str], 
                                          current_time: str):
        """
        清理失效的关系

        Args:
            session: Neo4j会话
            node_id: 源节点ID
            current_connections: 当前连接的节点字典
            current_time: 当前时间戳
        """
        # 获取所有现有的关系
        query = """
        MATCH (src:Node {node_id: $src_id})-[r:CONNECTED_TO]->(dst:Node)
        RETURN dst.node_id AS target_id, r.last_updated AS last_updated
        """
        result = await session.run(query, src_id=node_id)

        # 检查每个关系是否仍然有效
        async for record in result:
            target_id = record['target_id']
            last_updated = record['last_updated']

            # 如果连接不再存在或超过15分钟未更新，则禁用关系
            if str(target_id) not in current_connections or self._is_stale(last_updated, current_time):
                await session.run("""
                MATCH (src:Node {node_id: $src_id})-[r:CONNECTED_TO]->(dst:Node {node_id: $dst_id})
                SET r.active = false
                """, src_id=node_id, dst_id=target_id)
                logger.debug(f"禁用节点 {node_id} 到 {target_id} 的失效关系")

    def _is_stale(self, last_updated: str, current_time: str, threshold_minutes: int = 15) -> bool:
        """
        检查关系是否过期

        Args:
            last_updated: 最后更新时间
            current_time: 当前时间
            threshold_minutes: 过期阈值（分钟）

        Returns:
            bool: 关系是否过期
        """
        try:
            last_time = datetime.fromisoformat(last_updated)
            curr_time = datetime.fromisoformat(current_time)
            time_diff = (curr_time - last_time).total_seconds() / 60
            return time_diff > threshold_minutes
        except Exception as e:
            logger.error(f"检查关系过期状态失败: {e}")
            return True

    async def set_node_inactive(self, node_id: int):
        """
        设置节点为不活跃状态

        Args:
            node_id: 节点ID
        """
        async with self.driver.session() as session:
            await session.run("""
            MATCH (n:Node {node_id: $node_id})
            SET n.active = false, n.last_seen = $last_seen
            """, node_id=node_id, last_seen=datetime.now().isoformat())
            logger.debug(f"节点 {node_id} 已设置为不活跃状态")


class SnapshotScanner:
    """快照扫描器 - 负责扫描在线节点并计算优先级"""

    def __init__(self, redis_client, neo4j_manager):
        self.redis = redis_client
        self.neo4j = neo4j_manager
        self.priority_queue = RedisPriorityQueue(redis_client)
        self.session = None

    async def start(self):
        """启动快照扫描器"""
        logger.info("快照扫描器启动")
        while True:
            try:
                await self.scan_and_update()
                # 每5分钟运行一次
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"快照扫描器运行异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试

    async def scan_and_update(self):
        """扫描节点列表并更新优先级队列"""
        logger.info("开始扫描节点列表...")

        try:
            # 创建HTTP会话
            if not self.session:
                self.session = aiohttp.ClientSession()

            # 获取节点列表
            async with self.session.post(API_CONFIG['node_list_url']) as response:
                if response.status != 200:
                    logger.error(f"获取节点列表失败，状态码: {response.status}")
                    return

                json_data = await response.json()

                # 解析节点列表
                nodes = self._parse_node_list_json(json_data)
                logger.info(f"扫描到 {len(nodes)} 个在线节点")

                # 更新优先级队列
                await self._update_priority_queue(nodes)

                # 清理离线节点
                await self._cleanup_offline_nodes(nodes)

        except Exception as e:
            logger.error(f"扫描节点列表异常: {e}")
        finally:
            if self.session:
                await self.session.close()
                self.session = None

    def _parse_node_list(self, soup: BeautifulSoup) -> List[Dict]:
        """
        解析节点列表HTML

        Args:
            soup: BeautifulSoup对象

        Returns:
            List[Dict]: 节点列表
        """
        nodes = []
        try:
            # 这里需要根据实际的HTML结构进行解析
            # 示例代码，需要根据实际HTML结构调整
            table = soup.find('table', {'class': 'node-list'})
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:  # 跳过表头
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        node_id = cols[0].text.strip()
                        link_count = cols[1].text.strip()

                        if node_id.isdigit():
                            nodes.append({
                                'node_id': int(node_id),
                                'link_count': int(link_count) if link_count.isdigit() else 0
                            })
        except Exception as e:
            logger.error(f"解析节点列表HTML失败: {e}")

        return nodes

    def _parse_node_list_json(self, json_data: Dict) -> List[Dict]:
        """
        解析节点列表JSON数据

        Args:
            json_data: JSON响应数据

        Returns:
            List[Dict]: 节点列表
        """
        nodes = []
        try:
            data = json_data.get('data', [])
            for row in data:
                if not isinstance(row, list) or len(row) == 0:
                    continue

                # 第一列包含节点ID的HTML链接
                node_id_str = row[0] if isinstance(row[0], str) else ''
                # 提取节点ID（从HTML链接中提取）
                import re
                match = re.search(r'/stats/(\d+)', node_id_str)
                if match:
                    node_id_str = match.group(1)
                else:
                    # 如果没有找到链接，尝试直接提取数字
                    node_id_str = node_id_str.split()[0]  # 取第一部分作为节点ID

                if node_id_str.isdigit():
                    # 提取连接数（最后一列）
                    link_count = 0
                    if len(row) > 0:
                        try:
                            last_col = row[-1]  # 最后一列
                            link_count = int(last_col) if last_col and str(last_col).isdigit() else 0
                        except (ValueError, TypeError):
                            link_count = 0

                    nodes.append({
                        'node_id': int(node_id_str),
                        'link_count': link_count
                    })
        except Exception as e:
            logger.error(f"解析节点列表JSON失败: {e}")

        logger.info(f"从DataTables JSON数据中解析出 {len(nodes)} 个节点")
        return nodes

    async def _update_priority_queue(self, nodes: List[Dict]):
        """
        更新优先级队列

        优先级策略：直接使用连接数作为优先级分数
        - 连接数为0: 优先级分数为0
        - 连接数为1: 优先级分数为1
        - 连接数为5: 优先级分数为5
        - 以此类推...

        Args:
            nodes: 节点列表，每个节点应包含node_id和link_count
        """
        for node in nodes:
            node_id = node['node_id']
            link_count = node['link_count']

            # 直接使用连接数作为优先级分数
            priority = link_count

            # 检查节点是否已在队列中
            if not await self.priority_queue.is_in_queue(node_id):
                # 将节点加入优先级队列
                await self.priority_queue.enqueue(node_id, priority)
                logger.debug(f"节点 {node_id} 已加入队列，优先级: {priority} (连接数: {link_count})")

    async def _cleanup_offline_nodes(self, online_nodes: List[Dict]):
        """
        清理离线节点

        Args:
            online_nodes: 在线节点列表
        """
        # 获取在线节点ID集合
        online_node_ids = {node['node_id'] for node in online_nodes}

        # 从Neo4j获取所有活跃节点
        async with self.neo4j.driver.session() as session:
            result = await session.run("""
            MATCH (n:Node {active: true})
            RETURN n.node_id AS node_id
            """)

            # 检查每个活跃节点是否仍然在线
            async for record in result:
                node_id = record['node_id']
                if node_id not in online_node_ids:
                    # 节点已离线，设置为不活跃
                    await self.neo4j.set_node_inactive(node_id)
                    # 从优先级队列中移除
                    await self.priority_queue.remove_node(node_id)


class APIWorker:
    """异步工作者 - 负责从队列中获取节点并获取详细数据"""

    def __init__(self, redis_client, neo4j_manager, mysql_config: Dict):
        self.redis = redis_client
        self.neo4j = neo4j_manager
        self.mysql_config = mysql_config
        self.priority_queue = RedisPriorityQueue(redis_client)
        self.session = None
        self.rate_limiter = RateLimiter(API_CONFIG['rate_limit'], API_CONFIG['rate_limit_window'])

    async def start(self):
        """启动异步工作者"""
        logger.info("异步工作者启动")
        while True:
            try:
                await self.process_queue()
                # 短暂休眠后继续处理队列
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"异步工作者运行异常: {e}")
                await asyncio.sleep(10)  # 出错后等待10秒再重试

    async def process_queue(self):
        """处理优先级队列中的任务"""
        # 检查速率限制
        if not await self.rate_limiter.can_make_request():
            logger.debug("达到速率限制，等待...")
            await asyncio.sleep(1)
            return

        # 从队列中获取任务
        node_id = await self.priority_queue.dequeue()
        if not node_id:
            return

        try:
            # 获取节点详细数据
            node_data = await self._fetch_node_data(node_id)
            if node_data:
                # 更新Neo4j
                await self._update_neo4j(node_data)
                # 更新MySQL
                await self._update_mysql(node_data)
                logger.info(f"成功处理节点 {node_id}")
        except Exception as e:
            logger.error(f"处理节点 {node_id} 失败: {e}")

    async def _fetch_node_data(self, node_id: int) -> Optional[Dict]:
        """
        获取节点详细数据

        Args:
            node_id: 节点ID

        Returns:
            Optional[Dict]: 节点数据，如果获取失败则返回None
        """
        url = f"{API_CONFIG['base_url']}/{node_id}"

        # 创建HTTP会话
        if not self.session:
            self.session = aiohttp.ClientSession()

        # 带重试机制的请求
        for attempt in range(API_CONFIG['max_retries']):
            try:
                async with self.session.get(url) as response:
                    # 检查是否触发速率限制
                    if response.status == 429:
                        logger.warning(f"触发速率限制，冷却 {API_CONFIG['429_cooldown']} 秒")
                        await asyncio.sleep(API_CONFIG['429_cooldown'])
                        continue

                    if response.status != 200:
                        logger.warning(f"获取节点 {node_id} 数据失败，状态码: {response.status}")
                        return None

                    data = await response.json()
                    return self._parse_node_data(data)
            except Exception as e:
                logger.error(f"获取节点 {node_id} 数据异常 (尝试 {attempt + 1}/{API_CONFIG['max_retries']}): {e}")
                if attempt < API_CONFIG['max_retries'] - 1:
                    # 指数退避
                    backoff_time = API_CONFIG['retry_backoff'] ** (attempt + 1)
                    await asyncio.sleep(backoff_time)

        return None

    def _parse_node_data(self, data: Dict) -> Dict:
        """
        解析节点数据

        Args:
            data: 原始节点数据

        Returns:
            Dict: 解析后的节点数据
        """
        try:
            stats = data.get('stats', {})

            # 主节点数据从stats.user_node中获取
            user_node = stats.get('user_node', {})
            if not user_node:
                logger.warning("stats.user_node为空，无法解析节点数据")
                return {}

            # 节点server数据从stats.user_node.server获取
            server_info = user_node.get('server', {})

            # 连接的节点数据从stats.data.linkedNodes中获取
            node_data = stats.get('data', {})

            # 提取节点基本信息
            node_id_value = user_node.get('name', 0)

            # 解析node_frequency - 角色识别
            node_frequency = user_node.get('node_frequency', '')
            node_rank = 'Normal'  # 默认节点等级
            features = []  # 节点特性列表
            node_type = 'Unknown'  # 默认节点类型

            if node_frequency:
                # 中继模式 (Repeater)：若包含数字+频率特征（如 444.900）
                import re
                if re.search(r'\d+\.\d+', node_frequency):
                    # 包含频率特征，是中继模式
                    node_type = 'Repeater'
                # 枢纽模式 (Hub)：若包含文本描述（如 HUB, System, Network）
                elif any(keyword in node_frequency.upper() for keyword in ['HUB', 'SYSTEM', 'NETWORK']):
                    node_rank = 'Core'
                    node_type = 'Hub'
                    features.append(node_frequency)
                    node_frequency = ''  # 清空频率字段，因为这是特性描述

            # 解析node_tone - 业务识别
            node_tone = user_node.get('node_tone', '')
            tone = None
            location_desc = None

            if node_tone:
                try:
                    # 技术参数：若是纯数字（如 110.9）
                    if node_tone.replace('.', '', 1).isdigit():
                        tone = float(node_tone)
                    # 业务信息：若是域名或 URL
                    elif '.' in node_tone and not node_tone.replace('.', '', 1).isdigit():
                        location_desc = node_tone
                except (ValueError, TypeError):
                    pass

            # 解析server - 硬件画像
            site_name = server_info.get('SiteName', '')
            hardware_type = 'Unknown'

            if site_name:
                site_name_upper = site_name.upper()
                # Personal Station（个人站）：如果包含 Shack, Home, Residence
                if any(keyword in site_name_upper for keyword in ['SHACK', 'HOME', 'RESIDENCE']):
                    hardware_type = 'Personal Station'
                # Infrastructure（基础设施）：如果包含 Hub, Network, Data Center, Rack
                elif any(keyword in site_name_upper for keyword in ['HUB', 'NETWORK', 'DATA CENTER', 'RACK']):
                    hardware_type = 'Infrastructure'
                # Embedded Node（嵌入式节点）：如果包含 Pi, OrangePi, ClearNode, ARM, RASPBERRY PI
                elif any(keyword in site_name_upper for keyword in ['PI', 'ORANGEPI', 'CLEARNODE', 'ARM', 'RASPBERRY PI']):
                    hardware_type = 'Embedded Node'

            parsed_data = {
                'node_id': int(node_id_value) if isinstance(node_id_value, (int, str)) else 0,
                'callsign': user_node.get('callsign', ''),
                'node_type': node_type,  # Hub/Repeater/Unknown
                'lat': float(server_info.get('Latitude', 0.0) or 0.0),
                'lon': float(server_info.get('Logitude', 0.0) or 0.0),
                'uptime': int(node_data.get('apprptuptime', 0) or 0),
                'total_keyups': int(node_data.get('totalkeyups', 0) or 0),
                'total_tx_time': int(node_data.get('totaltxtime', 0) or 0),
                'last_seen': datetime.now().isoformat(),
                'linked_nodes': node_data.get('linkedNodes') or [],
                'connection_modes': node_data.get('nodes') or '',
                'source': 'allstarlink',  # 节点来源标识
                'node_rank': node_rank,  # 节点等级：Normal/Core
                'features': features,  # 节点特性列表
                'tone': tone,  # 技术参数：CTCSS/DCS
                'location_desc': location_desc,  # 业务信息描述
                'hardware_type': hardware_type  # 硬件类型
            }

            return parsed_data
        except Exception as e:
            logger.error(f"解析节点数据失败: {e}")
            return {}

    def _parse_linked_node_data(self, linked_node: Dict) -> Dict:
        """
        解析连接的节点数据

        Args:
            linked_node: 连接的节点原始数据

        Returns:
            Dict: 解析后的节点数据
        """
        try:
            # 获取节点ID
            # name字段是真正的节点ID（无论是AllStarLink节点还是其他电台节点）
            # Node_ID是数据库的自增ID，不是节点ID
            # 节点ID可能是整数或字符串（如'HP104104'）
            linked_node_id = linked_node.get('name')
            if not linked_node_id:
                logger.warning("连接节点缺少name字段")
                return {}

            # 直接使用linked_node_id，不强制转换为整数
            # 支持整数和字符串类型的节点ID
            node_id_value = linked_node_id if isinstance(linked_node_id, (int, str)) else str(linked_node_id)

            # 判断节点来源
            # 如果linked_node包含Node_ID字段，说明是AllStarLink节点
            # 否则，是其他电台节点
            is_allstarlink = 'Node_ID' in linked_node

            # 默认数据结构
            linked_node_data = {
                'node_id': node_id_value,
                'callsign': '',
                'node_type': 'Unknown',
                'lat': 0.0,
                'lon': 0.0,
                'uptime': 0,
                'total_keyups': 0,
                'total_tx_time': 0,
                'last_seen': datetime.now().isoformat(),
                'linked_nodes': [],
                'connection_modes': '',
                'connections': 0,  # 连接数
                'source': 'allstarlink' if is_allstarlink else 'other',
                'node_rank': 'Normal',
                'features': [],
                'tone': None,
                'location_desc': None,
                'hardware_type': 'Unknown'
            }

            # 只解析AllStarLink节点的详细数据
            if is_allstarlink:
                # 解析node_frequency - 角色识别
                node_frequency = linked_node.get('node_frequency', '')
                node_rank = 'Normal'
                features = []
                node_type = 'Unknown'

                if node_frequency:
                    import re
                    # 中继模式 (Repeater)：若包含数字+频率特征（如 444.900）
                    if re.search(r'\d+\.\d+', node_frequency):
                        node_type = 'Repeater'
                    # 枢纽模式 (Hub)：若包含文本描述（如 HUB, System, Network）
                    elif any(keyword in node_frequency.upper() for keyword in ['HUB', 'SYSTEM', 'NETWORK']):
                        node_rank = 'Core'
                        node_type = 'Hub'
                        features.append(node_frequency)

                # 解析node_tone - 业务识别
                node_tone = linked_node.get('node_tone', '')
                tone = None
                location_desc = None

                if node_tone:
                    try:
                        # 技术参数：若是纯数字（如 110.9）
                        if node_tone.replace('.', '', 1).isdigit():
                            tone = float(node_tone)
                        # 业务信息：若是域名或 URL
                        elif '.' in node_tone and not node_tone.replace('.', '', 1).isdigit():
                            location_desc = node_tone
                    except (ValueError, TypeError):
                        pass

                # 解析server - 硬件画像
                server_info = linked_node.get('server', {})
                site_name = server_info.get('SiteName', '')
                hardware_type = 'Unknown'

                if site_name:
                    site_name_upper = site_name.upper()
                    # Personal Station（个人站）：如果包含 Shack, Home, Residence
                    if any(keyword in site_name_upper for keyword in ['SHACK', 'HOME', 'RESIDENCE']):
                        hardware_type = 'Personal Station'
                    # Infrastructure（基础设施）：如果包含 Hub, Network, Data Center, Rack
                    elif any(keyword in site_name_upper for keyword in ['HUB', 'NETWORK', 'DATA CENTER', 'RACK']):
                        hardware_type = 'Infrastructure'
                    # Embedded Node（嵌入式节点）：如果包含 Pi, OrangePi, ClearNode, ARM, RASPBERRY PI
                    elif any(keyword in site_name_upper for keyword in ['PI', 'ORANGEPI', 'CLEARNODE', 'ARM', 'RASPBERRY PI']):
                        hardware_type = 'Embedded Node'

                # 更新AllStarLink节点的详细数据
                linked_node_data.update({
                    'callsign': linked_node.get('callsign', ''),
                    'node_type': node_type,
                    'lat': float(server_info.get('Latitude', 0.0) or 0.0),
                    'lon': float(server_info.get('Logitude', 0.0) or 0.0),
                    'node_rank': node_rank,
                    'features': features,
                    'tone': tone,
                    'location_desc': location_desc,
                    'hardware_type': hardware_type
                })

            return linked_node_data
        except Exception as e:
            logger.error(f"解析连接节点数据失败: {e}")
            return {}

    async def _update_neo4j(self, node_data: Dict):
        """
        更新Neo4j数据库

        Args:
            node_data: 节点数据
        """
        try:
            # 更新节点信息
            await self.neo4j.update_node(node_data)

            # 更新拓扑关系
            node_id = node_data.get('node_id')
            linked_nodes = node_data.get('linked_nodes', [])
            connection_modes = node_data.get('connection_modes', '')

            if node_id and linked_nodes:
                await self.neo4j.update_topology(node_id, linked_nodes, connection_modes)

                # 更新linkedNodes中的节点数据
                for linked_node in linked_nodes:
                    # 使用_parse_linked_node_data方法解析连接的节点数据
                    linked_node_data = self._parse_linked_node_data(linked_node)
                    if not linked_node_data:
                        continue

                    # 更新linked_node到Neo4j
                    await self.neo4j.update_node(linked_node_data)
                    logger.debug(f"已更新连接节点 {linked_node_data['node_id']} 的Neo4j数据")

        except Exception as e:
            logger.error(f"更新Neo4j失败: {e}")

    async def _update_mysql(self, node_data: Dict):
        """
        更新MySQL数据库

        Args:
            node_data: 节点数据
        """
        # 使用SQLAlchemy更新MySQL数据库
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.dialects.mysql import insert

            # 创建数据库连接
            db_url = (f"mysql+pymysql://{self.mysql_config['user']}:{self.mysql_config['password']}"
                     f"@{self.mysql_config['host']}/{self.mysql_config['database']}"
                     f"?charset={self.mysql_config['charset']}")

            engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

            # 提取节点数据
            node_id = node_data.get('node_id')
            if not node_id:
                logger.warning("节点数据缺少node_id，跳过MySQL更新")
                return

            # 准备更新数据
            update_data = {
                'node_id': node_id,
                'callsign': node_data.get('callsign', ''),
                'total_keyups': node_data.get('total_keyups', 0),
                'total_tx_time': node_data.get('total_tx_time', 0),
                'avg_talk_length': (node_data.get('total_tx_time', 0) / max(1, node_data.get('total_keyups', 1))),
                'latitude': node_data.get('lat', 0.0),
                'longitude': node_data.get('lon', 0.0),
                'last_seen': datetime.now(),
                'update_time': datetime.now()
            }

            # 计算当前连接数
            linked_nodes = node_data.get('linked_nodes', [])
            update_data['current_link_count'] = len(linked_nodes)

            # 使用UPSERT更新dim_nodes表
            with engine.connect() as conn:
                # 构建UPSERT语句
                stmt = text("""
                INSERT INTO dim_nodes 
                (node_id, callsign, total_keyups, total_tx_time, avg_talk_length, 
                 latitude, longitude, last_seen, update_time, current_link_count)
                VALUES 
                (:node_id, :callsign, :total_keyups, :total_tx_time, :avg_talk_length,
                 :latitude, :longitude, :last_seen, :update_time, :current_link_count)
                ON DUPLICATE KEY UPDATE
                callsign = VALUES(callsign),
                total_keyups = VALUES(total_keyups),
                total_tx_time = VALUES(total_tx_time),
                avg_talk_length = VALUES(avg_talk_length),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                last_seen = VALUES(last_seen),
                update_time = VALUES(update_time),
                current_link_count = VALUES(current_link_count)
                """)

                conn.execute(stmt, update_data)
                logger.debug(f"节点 {node_id} 数据已更新到MySQL")

                # 更新linkedNodes中的节点数据到MySQL
                # MySQL只存储AllStarLink节点（整数类型的节点ID）
                for linked_node in linked_nodes:
                    # 获取节点ID
                    # name字段是真正的节点ID（无论是AllStarLink节点还是其他电台节点）
                    # Node_ID是数据库的自增ID，不是节点ID
                    # 节点ID可能是整数或字符串（如'HP104104'）
                    linked_node_id = linked_node.get('name')
                    if not linked_node_id:
                        continue

                    # 只处理整数类型的节点ID
                    if isinstance(linked_node_id, int):
                        node_id_int = linked_node_id
                    elif isinstance(linked_node_id, str) and linked_node_id.isdigit():
                        node_id_int = int(linked_node_id)
                    else:
                        # 字符串类型的节点ID（如'HP104104'）跳过，不更新到MySQL
                        logger.debug(f"跳过字符串类型的节点ID: {linked_node_id}")
                        continue

                    # 准备linked_node的更新数据
                    linked_update_data = {
                        'node_id': node_id_int,
                        'callsign': linked_node.get('callsign', ''),
                        'total_keyups': 0,
                        'total_tx_time': 0,
                        'avg_talk_length': 0.0,
                        'latitude': 0.0,
                        'longitude': 0.0,
                        'last_seen': datetime.now(),
                        'update_time': datetime.now(),
                        'current_link_count': 0
                    }

                    # 更新linked_node到MySQL
                    conn.execute(stmt, linked_update_data)
                    logger.debug(f"已更新连接节点 {node_id_int} 的MySQL数据")

        except Exception as e:
            logger.error(f"更新MySQL失败: {e}")


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def can_make_request(self) -> bool:
        """
        检查是否可以发起请求

        Returns:
            bool: 是否可以发起请求
        """
        now = time.time()

        # 移除时间窗口外的请求记录
        self.requests = [t for t in self.requests if now - t < self.time_window]

        # 检查是否超过速率限制
        if len(self.requests) >= self.max_requests:
            return False

        # 记录本次请求
        self.requests.append(now)
        return True


async def main():
    """主函数"""
    # 初始化Redis连接
    redis_client = redis.Redis(
        host=REDIS_CONFIG['host'],
        port=REDIS_CONFIG['port'],
        password=REDIS_CONFIG['password'],
        db=REDIS_CONFIG['db']
    )

    # 初始化优先级队列并清空
    priority_queue = RedisPriorityQueue(redis_client)
    await priority_queue.clear()

    # 初始化Neo4j管理器
    neo4j_manager = Neo4jManager(NEO4J_CONFIG)
    await neo4j_manager.initialize_constraints()

    # 初始化MySQL配置
    mysql_config = {
        'host': '121.41.230.15',
        'user': 'root',
        'password': '0595',
        'database': 'allStarLink',
        'charset': 'utf8mb4'
    }

    try:
        # 创建并启动快照扫描器
        snapshot_scanner = SnapshotScanner(redis_client, neo4j_manager)
        scanner_task = asyncio.create_task(snapshot_scanner.start())

        # 创建并启动异步工作者
        api_worker = APIWorker(redis_client, neo4j_manager, mysql_config)
        worker_task = asyncio.create_task(api_worker.start())

        # 等待任务完成
        await asyncio.gather(scanner_task, worker_task)
    finally:
        # 清理资源
        await redis_client.close()
        await neo4j_manager.close()


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
