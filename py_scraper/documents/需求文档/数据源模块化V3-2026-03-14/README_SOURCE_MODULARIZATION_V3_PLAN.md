# 数据源模块化 V3 重构结果

本文档同步 `py_scraper` 当前已经落地的 V3 重构结果，重点说明最终结构、边界划分和当前完成状态。

## 1. 重构目标

本轮重构遵循以下原则：

1. 简单设计，不为分层而分层
2. 低耦合、高内聚
3. 全局只保留最薄运行框架
4. `allstarlink` 相关逻辑尽量收进自己的模块
5. 支持后续继续接入新的 link 数据源

## 2. 当前目录结构

```text
src/link_scraper/
├── app/
│   ├── bootstrap.py
│   ├── container.py
│   ├── context.py
│   ├── contracts.py
│   ├── scheduler.py
│   └── task_registry.py
├── config/
│   └── settings.py
├── database/
│   ├── base.py
│   ├── mysql_manager.py
│   └── neo4j_manager.py
├── modules/
│   ├── allstarlink/
│   │   ├── jobs/
│   │   ├── schedules/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── source/
│   │   ├── models/
│   │   │   ├── payload/
│   │   │   ├── domain/
│   │   │   └── record/
│   │   ├── mappers/
│   │   └── module.py
│   └── other_source/
│       └── ...
├── sources/
│   └── __init__.py
└── main.py
```

## 3. 边界划分

### 3.1 全局层

全局目录只保留真正共享的框架能力：

1. `app/`
   负责启动、装配、调度
2. `config/`
   负责共享运行配置
3. `database/`
   只负责数据库连接与基础执行
4. `sources/__init__.py`
   只保留 source 协议和统一装配入口

### 3.2 AllStarLink 模块

`modules/allstarlink/` 负责 `allstarlink` 的全部业务闭环：

1. source URL 和响应解析
2. payload / domain / record 模型
3. 爬虫抓取与解析逻辑
4. MySQL / Neo4j 业务写入逻辑
5. 任务调度定义

## 4. 当前爬虫链路

### 4.1 `node_topology` 主链

这是当前生产主链，流程如下：

1. `scanner` 抓取在线节点列表
2. 将列表转换成队列可消费数据
3. 批量更新 MySQL `dim_nodes` 的在线状态
4. 将需要深度抓取的节点写入 Redis 队列
5. `worker` 逐个消费节点详情
6. 解析成领域模型
7. 写入 Neo4j 图数据
8. 写入 MySQL 维表与 ODS 明细

### 4.2 `node_list_snapshot` 轻量任务

该任务仍然保留，但职责已收窄为：

1. 定时抓取在线节点列表
2. 生成节点数量摘要
3. 只写 Redis 最新摘要

说明：

- 已移除 `ods_node_list_snapshots` 相关 MySQL 落库逻辑
- 不再依赖不存在的历史快照表

## 5. 已完成内容

### 5.1 运行框架

已完成：

1. `main.py` 只保留启动职责
2. `AppContext` / `ScheduledJob` / `SourceModule` 协议落地
3. `TaskRegistry` 和 `AppScheduler` 落地
4. `bootstrap` / `container` 装配链路落地

### 5.2 AllStarLink 模块化

已完成：

1. `allstarlink` 代码已收敛到 `modules/allstarlink`
2. `node_topology` 主链已模块化
3. `node_list_snapshot` 已模块化
4. payload / domain / record 模型已收进模块内
5. source client / parser / mapper 已收进模块内
6. repository 已直接承载 MySQL / Neo4j 业务写入

### 5.3 旧兼容层清理

已清理：

1. 旧全局 `domain/`
2. 旧全局 `repositories/`
3. 旧 `scrapers/` 主链实现
4. 旧 `services/` 主链实现
5. 旧 `sources/allstarlink`
6. 旧 `sources/other_source`
7. `sources/base.py`
8. `sources/factory.py`

### 5.4 配置收口

已完成：

1. 全局 `settings` 只保留共享运行配置
2. `allstarlink` 的 URL 已下沉到 `settings.allstarlink.source`
3. `settings.api` / `APIConfig` 已移除

## 6. 当前状态

### 6.1 已经结项的部分

可以认为已完成：

1. `allstarlink` 主体模块化重构
2. 全局薄框架收口
3. 旧兼容层清理
4. 轻量多数据源骨架建立

### 6.2 未纳入本轮强制范围

当前不作为本轮阻塞项：

1. `other_source` 真实业务接入
2. 调度并发控制
3. 第三个真实数据源接入

## 7. 当前验证结果

测试命令：

```bash
python -m unittest discover -s tests
```

当前结果：

1. `32` 个测试通过

## 8. 结论

当前项目已经从“全局混装的单源抓取脚本”重构成：

1. 全局薄框架
2. `allstarlink` 模块内闭环
3. 可继续扩展的新数据源骨架

因此，本轮 V3 重构可以认为已经完成。
