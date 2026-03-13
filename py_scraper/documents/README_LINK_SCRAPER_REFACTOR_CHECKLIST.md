# 新版爬虫重构执行 Checklist

本文档是：

- `documents/README_LINK_SCRAPER_REFACTOR_PLAN.md`
- `documents/README_LINK_SCRAPER_REFACTOR_TASKS.md`

的执行版清单。

用途：

- 直接用于 issue 跟踪
- 直接用于项目看板拆解
- 直接用于分阶段验收

## Phase 1：建立扩展边界

- [ ] 创建 `src/link_scraper/sources/` 目录结构
- [ ] 创建 `src/link_scraper/sources/base.py`
- [ ] 创建 `src/link_scraper/sources/allstarlink/client.py`
- [ ] 创建 `src/link_scraper/sources/allstarlink/parser.py`
- [ ] 创建 `src/link_scraper/sources/allstarlink/mapper.py`
- [ ] 定义 `SourceClient` 抽象接口
- [ ] 定义 `SourceParser` 抽象接口
- [ ] 定义 `SourceMapper` 抽象接口
- [ ] 将节点详情请求逻辑从 `APIWorker` 抽离到 `allstarlink/client.py`
- [ ] 将节点列表请求逻辑从 `SnapshotScanner` 抽离到 `allstarlink/client.py`
- [ ] 将 `NodeParser` 中 AllStarLink 专有解析逻辑迁移到 `allstarlink/parser.py`
- [ ] 让 `APIWorker` 改为通过 source client 获取节点详情
- [ ] 让 `SnapshotScanner` 改为通过 source client 获取节点列表
- [ ] 保证 Phase 1 后现有抓取行为不变

### Phase 1 验收

- [ ] 主流程不再直接依赖 AllStarLink 的原始请求细节
- [ ] 主流程不再直接依赖 AllStarLink 的原始解析细节
- [ ] AllStarLink 成为第一套 source adapter 实现

## Phase 2：拆分领域模型与持久化模型

- [ ] 创建 `src/link_scraper/domain/` 目录
- [ ] 新增 `CanonicalNode`
- [ ] 新增 `CanonicalConnection`
- [ ] 新增 `CanonicalNodeBundle`
- [ ] 创建 `src/link_scraper/repositories/records.py`
- [ ] 新增 `GraphNodeRecord`
- [ ] 新增 `GraphConnectionRecord`
- [ ] 新增 `DimNodeRecord`
- [ ] 新增 `OdsNodeDetailRecord`
- [ ] 创建 Neo4j record mapper
- [ ] 创建 `dim_nodes` record mapper
- [ ] 创建 `ods_nodes_details` record mapper
- [ ] 让 source mapper 输出 canonical model
- [ ] 让数据库写入层开始接收 record 对象而不是全能 `Node`
- [ ] 逐步弱化旧 `Node` 模型在新流程中的使用

### Phase 2 验收

- [ ] `Node` 不再承担全部数据库字段职责
- [ ] canonical model 与数据库 record 分离
- [ ] Neo4j / MySQL 写入对象边界清晰

## Phase 3：瘦身流程编排代码

- [ ] 创建 `src/link_scraper/services/` 目录
- [ ] 新增 `NodeFetchService`
- [ ] 新增 `NodeParseService`
- [ ] 新增 `NodeSyncService`
- [ ] 新增 `OdsWriteService`
- [ ] 将请求逻辑迁入 `NodeFetchService`
- [ ] 将 canonical 解析逻辑迁入 `NodeParseService`
- [ ] 将主节点/子节点/关系同步流程迁入 `NodeSyncService`
- [ ] 将 ODS 写入流程迁入 `OdsWriteService`
- [ ] 将 `APIWorker` 改成轻量编排器
- [ ] 让 `APIWorker` 只保留取任务、调用服务、记录日志的职责

### Phase 3 验收

- [ ] `APIWorker` 显著缩短
- [ ] 主要业务流程转移到 service 层
- [ ] 服务职责单一，便于测试

## Phase 4：支持多数据源接入

- [ ] 新增第二个 source adapter 目录
- [ ] 为第二个 source 实现 client
- [ ] 为第二个 source 实现 parser
- [ ] 为第二个 source 实现 mapper
- [ ] 在配置中增加 `SOURCE_NAME`
- [ ] 创建 source factory
- [ ] 让主流程通过 factory 选择 source adapter
- [ ] 使用第二个 source 跑通节点列表抓取
- [ ] 使用第二个 source 跑通详情抓取
- [ ] 使用第二个 source 跑通 canonical model 映射
- [ ] 使用第二个 source 跑通 Neo4j 写入
- [ ] 使用第二个 source 跑通 MySQL 写入

### Phase 4 验收

- [ ] 新增数据源不需要复制一套主流程
- [ ] 主流程可以在多个 source adapter 之间复用

## 公共任务：测试

- [ ] 为节点列表解析补单元测试
- [ ] 为主节点解析补单元测试
- [ ] 为子节点解析补单元测试
- [ ] 为连接模式解析补单元测试
- [ ] 为 canonical model mapper 补单元测试
- [ ] 为 ODS JSON 序列化补单元测试
- [ ] 为 Redis 队列流程补集成测试
- [ ] 为 Neo4j 写入补集成测试
- [ ] 为 MySQL `dim_nodes` 写入补集成测试
- [ ] 为 MySQL `ods_nodes_details` 写入补集成测试

## 公共任务：模型与状态治理

- [ ] 为节点增加显式完整度状态字段
- [ ] 区分占位节点和完整节点
- [ ] 明确 source name 字段
- [ ] 明确 snapshot / batch 相关字段边界
- [ ] 明确 graph model 与 dim model 的字段映射规则

## 公共任务：命名优化

- [ ] 评估 `APIWorker` 是否重命名为更明确的业务名称
- [ ] 评估 `MySQLManager` 是否拆分并重命名为 repository
- [ ] 评估 `Neo4jManager` 是否重命名为 graph repository
- [ ] 评估 `NodeParser` 是否改为 source parser / mapper 命名

## 公共任务：文档同步

- [ ] 完成 Phase 1 后更新架构文档
- [ ] 完成 Phase 2 后更新模型文档
- [ ] 完成 Phase 3 后更新重构方案文档
- [ ] 完成 Phase 4 后补充多数据源接入说明

## 推荐最小启动集

如果下一轮只做一小批，建议先做以下 checklist：

- [ ] 创建 `sources/` 目录结构
- [ ] 定义 source adapter 抽象接口
- [ ] 抽离节点详情请求逻辑
- [ ] 抽离节点列表请求逻辑
- [ ] 抽离 AllStarLink 解析逻辑

## 推荐第二批

- [ ] 定义 canonical model
- [ ] 定义 persistence record
- [ ] 增加 mapper 层
- [ ] 抽出 `NodeFetchService`
- [ ] 将 `APIWorker` 改为轻量编排器

## 最终完成标准

- [ ] 新增一个数据源时不需要复制一套主流程
- [ ] `Node` 不再是全能对象
- [ ] source-specific 字段不再污染通用领域模型
- [ ] 数据库层只负责持久化，不负责业务判断
- [ ] 主流程可在多个 source adapter 之间复用
- [ ] 占位节点与完整节点状态可显式区分

