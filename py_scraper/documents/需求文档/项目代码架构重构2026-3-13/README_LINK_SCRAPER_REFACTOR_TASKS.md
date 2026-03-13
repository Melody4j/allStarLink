# 新版爬虫重构任务拆分清单

本文档更新为执行结果版，用于说明哪些任务已经完成，哪些任务当前明确不做。

## 1. 当前范围

当前范围固定如下：

- 当前生产主线只关注 `AllStarLink`
- 第二数据源只保留结构骨架
- 当前优先级不是继续扩 source，而是稳定现有主线

## 2. 已完成任务

## 2.1 Phase 1：建立扩展边界

已完成：

1. 创建 `src/link_scraper/sources/` 目录结构
2. 定义 `SourceClient / SourceParser / SourceMapper` 抽象协议
3. 将节点详情请求逻辑迁入 `sources/allstarlink/client.py`
4. 将节点列表请求逻辑迁入 `sources/allstarlink/client.py`
5. 将 AllStarLink 解析逻辑迁入 `sources/allstarlink/parser.py`
6. 让 `SnapshotScanner` 和 `NodeIngestionWorker` 通过 adapter 工作

## 2.2 Phase 2：拆分领域模型与持久化模型

已完成：

7. 新增 `CanonicalNode`
8. 新增 `CanonicalConnection`
9. 新增 `CanonicalNodeBundle`
10. 新增 `GraphNodeRecord`
11. 新增 `GraphConnectionRecord`
12. 新增 `DimNodeRecord`
13. 新增 `OdsNodeDetailRecord`
14. 新增 `GraphMapper / DimNodeMapper / OdsMapper`
15. 让数据库写入层兼容接收 record

## 2.3 Phase 3：瘦身流程编排代码

已完成：

16. 新增 `NodeFetchService`
17. 新增 `NodeParseService`
18. 新增 `NodeSyncService`
19. 新增 `OdsWriteService`
20. 将 `APIWorker` 改造成轻量编排器
21. 为 service 层接入 repository

## 2.4 Phase 4：多数据源骨架

已完成：

22. 增加 `SOURCE_NAME`
23. 新增 source factory
24. 让主流程通过 factory 选择 source
25. 新增 `sources/other_source/` 骨架

说明：

当前 Phase 4 只完成“骨架”，不代表第二数据源已真实接入。

## 2.5 测试与联调

已完成：

26. 补充 mapper 单元测试
27. 补充 service 单元测试
28. 补充 repository 单元测试
29. 补充 manager record 兼容测试
30. 补充 source factory 测试
31. 补充 `SnapshotScanner` 回归测试
32. 补充 `RelationalStorageManager.execute_query()` 回归测试
33. 完成一轮真实环境联调

## 2.6 命名治理

已完成：

34. 新增 `NodeIngestionWorker` 主用命名
35. 新增 `GraphStorageManager` 主用命名
36. 新增 `RelationalStorageManager` 主用命名
37. 主流程切换为新命名
38. 保留旧命名别名以兼容外部依赖

## 3. 当前未完成任务

## 3.1 显式建模数据完整度

当前未完成：

1. 为节点引入显式占位/完整状态字段
2. 在图模型、维表模型、ODS 模型中统一该状态语义

## 3.2 兼容层彻底清理

当前未完成：

1. 淘汰 `models/` 下旧兼容模型
2. 淘汰 `scrapers/node_parser.py` 兼容包装层
3. 删除旧命名别名

说明：

这些任务现在没有继续做，是出于稳定性考虑，而不是忘记处理。

## 3.3 第二数据源真实接入

当前未完成：

1. 为第二数据源实现真实 client
2. 为第二数据源实现真实 parser
3. 为第二数据源实现真实 mapper
4. 使用第二数据源跑通主流程

说明：

这是当前明确搁置的范围外任务，因为项目目前只关注 `AllStarLink`。

## 4. 当前建议保留的任务优先级

如果后续还要继续推进，建议优先处理：

1. 显式建模节点完整度
2. 逐步移除旧兼容模型和旧兼容别名
3. 视业务需要增加更多集成测试
4. 等第二站点明确后，再推进 `other_source` 的真实实现

## 5. 当前验收结论

截至 2026-03-13，本轮重构已经完成的验收结果是：

1. 主流程已经可复用
2. 数据源差异已经可隔离
3. 统一领域模型和存储模型已经分开
4. service / repository 分层已经形成
5. `AllStarLink` 主线已经通过真实联调

因此，当前这份任务清单应被视为“已执行任务记录 + 后续待办”，而不是初始待办列表。
