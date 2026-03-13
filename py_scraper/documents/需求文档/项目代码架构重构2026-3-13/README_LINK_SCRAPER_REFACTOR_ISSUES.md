# 新版爬虫重构 Issue 标题列表

本文档将重构任务转换为适合直接创建 issue 的标题列表，并按优先级排序。

优先级说明：

- `P0`：必须最先处理，直接决定后续是否能顺利展开重构
- `P1`：高优先级，属于第一批应完成的结构性改造
- `P2`：中优先级，用于完善模型边界和服务层
- `P3`：后续扩展与治理项

## P0

1. 定义新版爬虫 source adapter 抽象接口
2. 创建 `sources/` 与 `sources/allstarlink/` 基础目录结构
3. 将 AllStarLink 节点详情请求逻辑从 `APIWorker` 抽离到 source client
4. 将 AllStarLink 节点列表请求逻辑从 `SnapshotScanner` 抽离到 source client
5. 将 AllStarLink 节点解析逻辑从 `NodeParser` 抽离到 source parser
6. 让 `APIWorker` 通过 source client 获取节点详情
7. 让 `SnapshotScanner` 通过 source client 获取节点列表
8. 保证 source adapter 第一轮落地后现有行为不变

## P1

9. 定义统一 canonical 领域模型 `CanonicalNode`
10. 定义统一 canonical 领域模型 `CanonicalConnection`
11. 定义统一 canonical 聚合模型 `CanonicalNodeBundle`
12. 定义 Neo4j 持久化 record 模型
13. 定义 `dim_nodes` 持久化 record 模型
14. 定义 `ods_nodes_details` 持久化 record 模型
15. 新增 canonical model 到 graph record 的映射层
16. 新增 canonical model 到 `dim_nodes` record 的映射层
17. 新增 canonical model 到 ODS record 的映射层
18. 降级旧 `Node` 模型职责并减少新流程对它的依赖

## P2

19. 创建 `NodeFetchService` 并迁移节点详情抓取逻辑
20. 创建 `NodeParseService` 并迁移 canonical 解析逻辑
21. 创建 `NodeSyncService` 并迁移主节点/子节点/关系同步逻辑
22. 创建 `OdsWriteService` 并迁移 ODS 写入逻辑
23. 将 `APIWorker` 重构为轻量编排器
24. 将数据库层重构为明确的 repository 角色
25. 拆分 `MySQLManager` 为 `dim_nodes` 与 ODS 独立仓储
26. 将 `Neo4jManager` 收敛为 graph repository

## P3

27. 为节点增加显式完整度状态字段
28. 为节点增加显式 source 标识字段
29. 为节点增加显式占位/完整状态建模
30. 创建 source factory 以支持多数据源实例化
31. 在配置中增加 `SOURCE_NAME` 切换机制
32. 新增第二个 source adapter 并验证主流程复用
33. 为节点列表解析补充单元测试
34. 为主节点解析补充单元测试
35. 为子节点解析补充单元测试
36. 为连接模式解析补充单元测试
37. 为 mapper 层补充单元测试
38. 为 Redis 队列流程补充集成测试
39. 为 Neo4j 写入补充集成测试
40. 为 `dim_nodes` 写入补充集成测试
41. 为 `ods_nodes_details` 写入补充集成测试
42. 统一核心类命名并从 manager/worker 命名迁移到业务角色命名
43. 在每阶段完成后同步更新架构与模型文档

## 推荐建 issue 的第一批顺序

如果只创建第一批 issue，建议按以下顺序建立：

1. 定义新版爬虫 source adapter 抽象接口
2. 创建 `sources/` 与 `sources/allstarlink/` 基础目录结构
3. 将 AllStarLink 节点详情请求逻辑从 `APIWorker` 抽离到 source client
4. 将 AllStarLink 节点列表请求逻辑从 `SnapshotScanner` 抽离到 source client
5. 将 AllStarLink 节点解析逻辑从 `NodeParser` 抽离到 source parser
6. 让 `APIWorker` 通过 source client 获取节点详情
7. 让 `SnapshotScanner` 通过 source client 获取节点列表
8. 保证 source adapter 第一轮落地后现有行为不变

## 推荐建 issue 的第二批顺序

1. 定义统一 canonical 领域模型 `CanonicalNode`
2. 定义统一 canonical 领域模型 `CanonicalConnection`
3. 定义统一 canonical 聚合模型 `CanonicalNodeBundle`
4. 定义 Neo4j 持久化 record 模型
5. 定义 `dim_nodes` 持久化 record 模型
6. 定义 `ods_nodes_details` 持久化 record 模型
7. 新增 canonical model 到 graph record 的映射层
8. 新增 canonical model 到 `dim_nodes` record 的映射层
9. 新增 canonical model 到 ODS record 的映射层
10. 降级旧 `Node` 模型职责并减少新流程对它的依赖

## 推荐建 issue 的第三批顺序

1. 创建 `NodeFetchService` 并迁移节点详情抓取逻辑
2. 创建 `NodeParseService` 并迁移 canonical 解析逻辑
3. 创建 `NodeSyncService` 并迁移主节点/子节点/关系同步逻辑
4. 创建 `OdsWriteService` 并迁移 ODS 写入逻辑
5. 将 `APIWorker` 重构为轻量编排器
6. 将数据库层重构为明确的 repository 角色

