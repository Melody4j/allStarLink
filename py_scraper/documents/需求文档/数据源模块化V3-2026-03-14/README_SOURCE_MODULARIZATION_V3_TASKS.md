# 数据源模块化 V3 任务清单

本文档记录本轮 V3 重构的任务拆分与最终完成状态。

## 1. Phase 0 边界定义

状态：已完成

完成内容：

1. 明确 `app / modules / database / sources` 的边界
2. 明确 `main.py` 只做启动
3. 明确业务尽量收进 `modules/<source>/`

## 2. Phase 1 运行框架

状态：已完成

完成内容：

1. 新增 `app/bootstrap.py`
2. 新增 `app/container.py`
3. 新增 `app/context.py`
4. 新增 `app/contracts.py`
5. 新增 `app/scheduler.py`
6. 新增 `app/task_registry.py`
7. `main.py` 收敛成启动入口

## 3. Phase 2 Source Module 骨架

状态：已完成

完成内容：

1. 新增 `modules/allstarlink/module.py`
2. 新增 `modules/other_source/module.py`
3. `bootstrap` 已支持按 `source_name` 装配模块

## 4. Phase 3 AllStarLink 主链迁移

状态：已完成

完成内容：

1. `node_topology` 已迁入 `modules/allstarlink`
2. 主链拆分为 `jobs / schedules / services / repositories`
3. 主链已不再依赖旧 `scrapers/` 和旧 `services/`
4. Redis 队列、节点扫描、详情消费、图写入、MySQL 写入已全部接到模块内实现

## 5. Phase 4 持久化语义下沉

状态：已完成

完成内容：

1. 旧全局 `repositories/` 已删除
2. Neo4j 写入语义已落到 `modules/allstarlink/repositories`
3. MySQL `dim_nodes` 更新语义已落到 `modules/allstarlink/repositories`
4. MySQL `ods_nodes_details` 插入语义已落到 `modules/allstarlink/repositories`
5. `database/` 只保留基础执行能力

说明：

- `repositories` 现在直接负责业务 SQL / Cypher 执行
- 不再额外引入 `gateway` 层

## 6. Phase 5 第二个 AllStarLink 任务

状态：已完成

完成内容：

1. 新增 `node_list_snapshot` 任务
2. 任务只负责在线节点列表摘要
3. 当前只写 Redis 最新摘要
4. 已移除对不存在表 `ods_node_list_snapshots` 的写入逻辑

## 7. Phase 6 Source 层收口

状态：已完成

完成内容：

1. `allstarlink` source 实现已收进 `modules/allstarlink/source`
2. `other_source` source 骨架已收进 `modules/other_source/source`
3. 全局 `sources/` 已压缩为单文件注册层
4. `sources/base.py` 和 `sources/factory.py` 已删除

## 8. Phase 7 模型收口

状态：已完成

完成内容：

1. `payload` 模型已建立
   - `AslNodeOnlineListPayload`
   - `AslNodeDetailsPayload`
2. 领域模型已收进 `modules/allstarlink/models/domain`
3. 持久化记录模型已收进 `modules/allstarlink/models/record`
4. 原全局 `domain/` 已删除

## 9. Phase 8 配置收口

状态：已完成

完成内容：

1. 全局共享配置保留在 `config/settings.py`
2. `allstarlink` source URL 已下沉到 `settings.allstarlink.source`
3. 原 `settings.api` 配置链路已删除

## 10. Phase 9 日志增强

状态：已完成

完成内容：

1. 节点扫描关键日志已补充
2. `node_topology` MySQL 维表更新日志已补充
3. `node_topology` MySQL ODS 插入日志已补充
4. `node_topology` Neo4j 节点 upsert 日志已补充
5. `node_topology` Neo4j 拓扑关系更新/创建日志已补充
6. 离线节点删除日志已补充

## 11. 当前不做项

本轮明确不做：

1. 调度并发控制
2. `other_source` 真实业务接入
3. 第三个真实数据源接入

## 12. 当前验证结果

测试命令：

```bash
python -m unittest discover -s tests
```

结果：

1. `32` 个测试通过
