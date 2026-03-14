# 新版爬虫重构执行 Checklist

本文档按当前执行结果更新，使用 `[x]` / `[ ]` 标注状态。

## Phase 1：建立扩展边界

- [x] 创建 `src/link_scraper/sources/` 目录结构
- [x] 创建 `src/link_scraper/sources/base.py`
- [x] 创建 `src/link_scraper/sources/allstarlink/client.py`
- [x] 创建 `src/link_scraper/sources/allstarlink/parser.py`
- [x] 创建 `src/link_scraper/sources/allstarlink/mapper.py`
- [x] 定义 `SourceClient` 抽象接口
- [x] 定义 `SourceParser` 抽象接口
- [x] 定义 `SourceMapper` 抽象接口
- [x] 将节点详情请求逻辑从 `APIWorker` 抽离到 `allstarlink/client.py`
- [x] 将节点列表请求逻辑从 `SnapshotScanner` 抽离到 `allstarlink/client.py`
- [x] 将 `NodeParser` 中 AllStarLink 专有解析逻辑迁移到 `allstarlink/parser.py`
- [x] 让 `APIWorker` 改为通过 source client 获取节点详情
- [x] 让 `SnapshotScanner` 改为通过 source client 获取节点列表
- [x] 保证 Phase 1 后现有抓取行为不变

### Phase 1 验收

- [x] 主流程不再直接依赖 AllStarLink 的原始请求细节
- [x] 主流程不再直接依赖 AllStarLink 的原始解析细节
- [x] AllStarLink 成为第一套 source adapter 实现

## Phase 2：拆分领域模型与持久化模型

- [x] 创建 `src/link_scraper/domain/` 目录
- [x] 新增 `CanonicalNode`
- [x] 新增 `CanonicalConnection`
- [x] 新增 `CanonicalNodeBundle`
- [x] 创建 `src/link_scraper/repositories/records.py`
- [x] 新增 `GraphNodeRecord`
- [x] 新增 `GraphConnectionRecord`
- [x] 新增 `DimNodeRecord`
- [x] 新增 `OdsNodeDetailRecord`
- [x] 创建 Neo4j record mapper
- [x] 创建 `dim_nodes` record mapper
- [x] 创建 `ods_nodes_details` record mapper
- [x] 让 source mapper 输出 canonical model
- [x] 让数据库写入层开始接收 record 对象而不是全能 `Node`
- [x] 逐步弱化旧 `Node` 模型在新流程中的使用

### Phase 2 验收

- [x] `Node` 不再承担全部数据库字段职责
- [x] canonical model 与数据库 record 分离
- [x] Neo4j / MySQL 写入对象边界清晰

## Phase 3：瘦身流程编排代码

- [x] 创建 `src/link_scraper/services/` 目录
- [x] 新增 `NodeFetchService`
- [x] 新增 `NodeParseService`
- [x] 新增 `NodeSyncService`
- [x] 新增 `OdsWriteService`
- [x] 将请求逻辑迁入 `NodeFetchService`
- [x] 将 canonical 解析逻辑迁入 `NodeParseService`
- [x] 将主节点/子节点/关系同步流程迁入 `NodeSyncService`
- [x] 将 ODS 写入流程迁入 `OdsWriteService`
- [x] 将 `APIWorker` 改成轻量编排器
- [x] 让 `APIWorker` 只保留取任务、调用服务、记录日志的职责

### Phase 3 验收

- [x] `APIWorker` 显著缩短
- [x] 主要业务流程转移到 service 层
- [x] 服务职责单一，便于测试

## Phase 4：支持多数据源接入

- [x] 新增第二个 source adapter 目录
- [ ] 为第二个 source 实现真实 client
- [ ] 为第二个 source 实现真实 parser
- [ ] 为第二个 source 实现真实 mapper
- [x] 在配置中增加 `SOURCE_NAME`
- [x] 创建 source factory
- [x] 让主流程通过 factory 选择 source adapter
- [ ] 使用第二个 source 跑通节点列表抓取
- [ ] 使用第二个 source 跑通详情抓取
- [ ] 使用第二个 source 跑通 canonical model 映射
- [ ] 使用第二个 source 跑通 Neo4j 写入
- [ ] 使用第二个 source 跑通 MySQL 写入

### Phase 4 验收

- [x] 新增数据源不需要复制一套主流程
- [x] 主流程可以在多个 source adapter 之间复用

说明：

Phase 4 当前按“骨架完成”验收，未推进第二数据源真实实现。

## 公共任务：测试

- [x] 为节点列表解析补单元测试
- [x] 为主节点解析补单元测试
- [x] 为子节点解析补单元测试
- [x] 为连接模式解析补单元测试
- [x] 为 canonical model mapper 补单元测试
- [x] 为 ODS JSON 序列化补单元测试
- [x] 为 repository 委派行为补单元测试
- [x] 为 manager record 兼容行为补单元测试
- [x] 为 `SnapshotScanner` 回归问题补测试
- [x] 为 `RelationalStorageManager.execute_query()` 回归问题补测试
- [x] 完成真实 Redis / MySQL / Neo4j / 远端 API 单轮联调

## 公共任务：模型与状态治理

- [ ] 为节点增加显式完整度状态字段
- [ ] 区分占位节点和完整节点
- [ ] 明确 source name 字段是否进入 canonical model
- [ ] 明确 snapshot / batch 相关字段边界
- [x] 明确 graph model 与 dim model 的字段映射规则

## 公共任务：命名优化

- [x] 将主流程主用命名调整为 `NodeIngestionWorker`
- [x] 将主流程主用命名调整为 `RelationalStorageManager`
- [x] 将主流程主用命名调整为 `GraphStorageManager`
- [x] 保留旧命名别名以兼容外部依赖
- [x] 移除旧命名别名

## 公共任务：文档同步

- [x] 更新架构文档
- [x] 更新模型文档
- [x] 更新重构方案文档
- [x] 更新限制说明文档
- [x] 更新执行清单和进度文档

## 当前未收口项

- [ ] 为节点完整度做显式建模
- [ ] 当第二数据源目标明确后，实现真实 `other_source`

## 当前完成标准结论

- [x] 新增一个数据源时不需要复制一套主流程
- [x] source-specific 字段不再直接污染通用主流程
- [x] 数据库层与主流程边界已经明显收敛
- [x] 主流程可在多个 source adapter 之间复用
- [ ] 占位节点与完整节点状态可显式区分
