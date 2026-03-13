# 新版爬虫重构任务拆分清单

本文档基于：

- `documents/README_LINK_SCRAPER_REFACTOR_PLAN.md`

目标是把重构方案拆分成可执行的任务列表，方便后续按阶段推进、创建 issue、安排迭代。

本文档按以下原则组织：

- 每个阶段尽量可独立交付
- 每个任务尽量可单独提交
- 优先降低耦合，再做命名和美化
- 优先保证行为不变，再逐步提升结构

## 1. 总体目标

这次重构要达到的结果是：

1. 主流程可以复用
2. 数据源差异可以隔离
3. 领域模型职责清晰
4. 数据库存储对象清晰
5. 后续接入其他网站时尽量新增代码而不是修改主流程

## 2. 重构阶段总览

建议分为 4 个阶段：

1. 建立扩展边界
2. 拆分领域模型和持久化模型
3. 瘦身流程编排代码
4. 支持多数据源接入

## 3. 第一阶段：建立扩展边界

### 3.1 阶段目标

- 不改变当前业务行为
- 先建立 source adapter 边界
- 把 AllStarLink 相关逻辑从主流程中隔离出来

### 3.2 任务清单

#### 任务 1：创建 source adapter 目录结构

目标：

- 建立新的扩展目录，不影响现有逻辑

建议产出：

```text
src/link_scraper/sources/
├─ __init__.py
├─ base.py
└─ allstarlink/
   ├─ __init__.py
   ├─ client.py
   ├─ parser.py
   └─ mapper.py
```

验收标准：

- 新目录可导入
- 不影响现有运行

#### 任务 2：定义 source adapter 抽象接口

目标：

- 为后续多数据源接入建立统一契约

建议内容：

- `SourceClient`
- `SourceParser`
- `SourceMapper`

建议接口示例：

```python
class SourceClient(Protocol):
    async def fetch_node_list(self) -> dict: ...
    async def fetch_node_detail(self, node_id: str) -> dict: ...

class SourceMapper(Protocol):
    def map_node_list(self, payload: dict) -> list: ...
    def map_node_detail(self, payload: dict): ...
```

验收标准：

- 接口定义完成
- AllStarLink 逻辑可以逐步接入该接口

#### 任务 3：抽离节点详情请求逻辑

当前来源：

- `src/link_scraper/scrapers/api_worker.py`

目标：

- 把 `_fetch_node_data()` 移入 `sources/allstarlink/client.py`

任务内容：

- 新建 `AllStarLinkClient`
- 搬迁请求 URL 拼装、会话管理、重试逻辑
- 保持对 `APIWorker` 的调用结果不变

验收标准：

- `APIWorker` 不再直接请求详情接口
- 功能行为不变

#### 任务 4：抽离节点列表请求逻辑

当前来源：

- `src/link_scraper/scrapers/snapshot_scanner.py`

目标：

- 把节点列表请求移入 `sources/allstarlink/client.py`

任务内容：

- 新增 `fetch_node_list()`
- 将 `nodeList` 请求从 `SnapshotScanner` 中移出

验收标准：

- `SnapshotScanner` 只负责调用 client，不直接拼请求

#### 任务 5：抽离 AllStarLink 解析逻辑

当前来源：

- `src/link_scraper/scrapers/node_parser.py`

目标：

- 将 AllStarLink 专有解析逻辑迁移到 `sources/allstarlink/parser.py`

任务内容：

- 迁移 `parse_node()`
- 迁移 `parse_linked_node()`
- 迁移 `parse_connections()`
- 迁移 `_parse_connection_modes()`
- 迁移 `_parse_node_info()`
- 迁移 `_parse_business_info()`
- 迁移 `_parse_hardware_type()`

验收标准：

- 主流程不再直接依赖 AllStarLink 专有解析器文件名
- 现有功能不变

#### 任务 6：让旧主流程改为依赖 adapter

目标：

- `APIWorker` 和 `SnapshotScanner` 通过 source adapter 调用

任务内容：

- 在初始化时注入 AllStarLink client/parser
- 保持当前 `main.py` 主流程不变

验收标准：

- 主流程仍可运行
- 但 AllStarLink 逻辑已开始从主流程中剥离

### 3.3 第一阶段交付结果

完成后应该达到：

- 主流程开始依赖抽象接口
- AllStarLink 成为第一套 source adapter 实现
- 不改数据库模型，不改输出结构

## 4. 第二阶段：拆分领域模型与持久化模型

### 4.1 阶段目标

- 把全能 `Node` 模型拆小
- 将领域模型与数据库存储对象解耦

### 4.2 任务清单

#### 任务 7：定义统一领域模型

目标：

- 建立 source 无关的 canonical 模型

建议新增：

- `CanonicalNode`
- `CanonicalConnection`
- `CanonicalNodeBundle`

建议位置：

```text
src/link_scraper/domain/
├─ __init__.py
└─ models.py
```

验收标准：

- 统一领域模型可承接 AllStarLink 映射结果

#### 任务 8：定义持久化 record 模型

目标：

- 为不同存储目标建立独立 record

建议新增：

- `GraphNodeRecord`
- `GraphConnectionRecord`
- `DimNodeRecord`
- `OdsNodeDetailRecord`

建议位置：

```text
src/link_scraper/repositories/
├─ __init__.py
└─ records.py
```

验收标准：

- 不同数据库写入所需字段不再堆在一个 `Node` 类里

#### 任务 9：新增 mapping 层

目标：

- 把 canonical 模型映射到不同持久化 record

建议新增：

- `GraphMapper`
- `DimNodeMapper`
- `OdsMapper`

验收标准：

- 数据库层不再直接吃 `Node`

#### 任务 10：逐步弱化旧 `Node` 模型

目标：

- 将旧 `Node` 从中心模型降级为过渡对象，最终淘汰

任务内容：

- 新代码优先使用 `CanonicalNode`
- 逐步减少 `Node` 在新逻辑中的使用

验收标准：

- 新增功能不再依赖旧 `Node`

### 4.3 第二阶段交付结果

完成后应该达到：

- source adapter 输出 canonical model
- canonical model 通过 mapper 转成不同存储 record
- 数据库层开始与领域模型解耦

## 5. 第三阶段：瘦身流程编排代码

### 5.1 阶段目标

- 拆解 `APIWorker`
- 建立更清晰的服务层职责

### 5.2 任务清单

#### 任务 11：抽出 NodeFetchService

目标：

- 将请求、重试、错误处理从 `APIWorker` 中独立出来

建议位置：

```text
src/link_scraper/services/fetch_service.py
```

#### 任务 12：抽出 NodeParseService

目标：

- 将解析主节点、子节点、连接关系的行为独立出来

建议位置：

```text
src/link_scraper/services/parse_service.py
```

#### 任务 13：抽出 NodeSyncService

目标：

- 将主节点、子节点、关系的同步流程独立出来

任务内容：

- 同步主节点图数据
- 同步子节点图数据
- 同步拓扑关系
- 处理保留统计字段等写入策略

建议位置：

```text
src/link_scraper/services/sync_service.py
```

#### 任务 14：抽出 OdsWriteService

目标：

- 将 ODS 快照构建和写入独立出来

建议位置：

```text
src/link_scraper/services/ods_service.py
```

#### 任务 15：将 `APIWorker` 改为轻量编排器

目标：

- 让 `APIWorker` 只负责：
  - 取任务
  - 调 fetch service
  - 调 parse service
  - 调 sync service
  - 记录日志

验收标准：

- `APIWorker` 的代码显著缩短
- 每个服务职责单一

### 5.3 第三阶段交付结果

完成后应该达到：

- 流程清晰
- 类体积缩小
- 更容易测试
- 变更影响范围可控

## 6. 第四阶段：支持多数据源接入

### 6.1 阶段目标

- 在不修改主流程的前提下接入第二个网站

### 6.2 任务清单

#### 任务 16：新增第二个 source adapter

目标：

- 新增一个新的数据源目录，例如：

```text
src/link_scraper/sources/other_source/
├─ client.py
├─ parser.py
└─ mapper.py
```

#### 任务 17：接入配置切换

目标：

- 在配置中增加 source 选择项

例如：

- `SOURCE_NAME=allstarlink`
- `SOURCE_NAME=other_source`

#### 任务 18：实现 source 工厂

目标：

- 按配置实例化不同 source client / parser / mapper

建议位置：

```text
src/link_scraper/sources/factory.py
```

#### 任务 19：验证主流程复用

目标：

- 用第二个数据源跑通相同流程：
  - 节点列表抓取
  - 详情抓取
  - 统一领域模型转换
  - Neo4j / MySQL 写入

验收标准：

- 主流程无需复制一份新 worker
- 仅新增 source 目录和少量接入代码

### 6.3 第四阶段交付结果

完成后应该达到：

- 真正形成多数据源抓取框架
- 新增网站主要是新增 source adapter，而不是修改主流程

## 7. 跨阶段公共任务

这些任务不强制属于某一阶段，但建议穿插进行。

### 任务 20：补单元测试

优先测试对象：

- 节点列表解析
- 主节点解析
- 子节点解析
- 连接模式解析
- Mapper 映射逻辑
- ODS JSON 序列化逻辑

### 任务 21：补集成测试

优先覆盖：

- Redis 入队/出队
- 节点抓取到落库主流程
- Neo4j 节点和关系写入
- MySQL `dim_nodes` / `ods_nodes_details` 写入

### 任务 22：补文档

建议在每个阶段结束时同步更新：

- 架构说明文档
- 模型说明文档
- 当前限制说明文档

### 任务 23：命名统一

这项建议放在边界稳定后执行。

可以考虑逐步调整为：

- `APIWorker` -> `NodeIngestionWorker`
- `MySQLManager` -> `DimNodeRepository` / `OdsRepository`
- `Neo4jManager` -> `GraphRepository`
- `NodeParser` -> `AllStarLinkNodeMapper` 或 `SourceParser`

## 8. 推荐提交拆分方式

为了控制风险，建议每个任务尽量单独提交或小批量提交。

推荐粒度：

1. 目录与接口定义
2. source client 抽离
3. parser 抽离
4. canonical model 引入
5. persistence record 引入
6. mapper 引入
7. service 层拆分
8. worker 瘦身
9. 第二数据源接入

不建议：

- 一次性把模型、流程、数据库层、命名全部改掉

## 9. 第一批最值得先做的任务

如果下一次只做一小轮重构，优先建议做以下 5 个任务：

1. 任务 1：创建 `sources/` 目录结构
2. 任务 2：定义 source adapter 接口
3. 任务 3：抽离节点详情请求逻辑
4. 任务 4：抽离节点列表请求逻辑
5. 任务 5：抽离 AllStarLink 解析逻辑

这一批任务的收益最大，因为它们可以最先把“多网站接入能力”建立起来。

## 10. 第二批建议任务

如果第一批完成，第二批优先建议做：

1. 任务 7：定义 canonical model
2. 任务 8：定义 persistence record
3. 任务 9：新增 mapping 层
4. 任务 11：抽出 NodeFetchService
5. 任务 15：将 `APIWorker` 改为轻量编排器

## 11. 最终验收标准

当整轮重构完成后，应满足以下条件：

1. 新增一个网站时，不需要复制一套 `APIWorker`
2. `Node` 不再是全能对象
3. source-specific 字段不会直接污染通用领域模型
4. 数据库层只负责存储，不负责业务判断
5. 主流程可以在不同 source adapter 间复用
6. 占位节点和完整节点状态可以显式区分

## 12. 建议使用方式

后续执行重构时，建议：

1. 以本文档为任务清单
2. 每个任务建立单独 issue 或 checklist
3. 每完成一个阶段，同步更新：
   - `README_LINK_SCRAPER_ARCHITECTURE.md`
   - `README_LINK_SCRAPER_MODELS.md`
   - `README_LINK_SCRAPER_REFACTOR_PLAN.md`

这样可以保证架构演进和文档演进同步，不会再次出现“代码已变，文档已经失效”的问题。

