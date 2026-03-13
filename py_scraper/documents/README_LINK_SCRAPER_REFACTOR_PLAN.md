# 新版爬虫重构方案与缘由

本文档基于当前 `src/link_scraper` 代码现状，说明为什么需要重构、当前架构存在的主要问题、未来支持多网站采集时会遇到的扩展障碍，以及一套可执行的分阶段重构方案。

本文档的目标不是评价代码“能不能跑”，而是为下一次正式重构提供设计依据和迁移路线。

## 1. 重构背景

当前新版爬虫已经具备以下能力：

- 基于 Redis 优先级队列调度节点抓取
- 抓取 AllStarLink 在线节点列表和节点详情
- 将节点和连接关系写入 Neo4j
- 将当前节点状态和 ODS 明细写入 MySQL

从“功能可用”的角度看，当前版本是可运行的。

但从以下目标来看，当前结构已经接近上限：

- 提升代码可读性
- 提升模块职责清晰度
- 降低维护成本
- 支持后续接入其他网站的数据抓取
- 让当前流程可以复用，而不是复制一份新代码再改

如果后续计划继续接入第二个、第三个数据源，那么当前代码结构不建议继续堆叠功能，而应该先重构。

## 2. 当前代码的主要问题

## 2.1 `Node` 模型职责过重

当前 `Node` 模型定义在：

- `src/link_scraper/models/node.py`

这个类目前同时承担了多种职责：

1. 领域对象
2. AllStarLink API 解析结果载体
3. Neo4j 节点属性载体
4. MySQL `dim_nodes` 字段载体
5. 批次号上下文载体
6. 子节点占位数据载体

这会导致几个直接问题：

- 字段数量过多，阅读困难
- 某些字段只对某个存储层有意义，但被塞进统一模型
- 某些字段只对某个数据源有意义，但被当作通用字段保留
- 模型一旦变动，会同时影响解析层、数据库层、图模型层、ODS 层

### 典型表现

- `Node` 同时包含 `site_name`、`history_total_keyups`、`batch_no`、`unique_id` 等不同层次的字段
- 子节点缺失统计值时，需要通过 `None`/`0` 来表达状态，但没有显式的数据完整度模型

### 结论

`Node` 不应该继续作为“全能对象”存在。

## 2.2 `APIWorker` 过于臃肿

当前 `APIWorker` 定义在：

- `src/link_scraper/scrapers/api_worker.py`

它目前承担了：

1. 任务消费
2. 节点详情请求
3. 限流控制
4. 重试逻辑
5. 原始数据解析
6. 子节点构造
7. Neo4j 节点写入
8. Neo4j 关系写入
9. MySQL 主节点更新
10. MySQL 子节点更新
11. ODS 明细写入

也就是说，这个类已经既是：

- worker
- service
- orchestrator
- fetcher
- sync pipeline

这类类通常在单一数据源的早期实现中很常见，但一旦业务复杂化，维护成本会快速升高。

### 具体问题

- 类太大，阅读成本高
- 很难单元测试
- 修改任一流程都容易影响整个链路
- 后续新增其他站点时，最容易的方式会变成复制一份 `APIWorker`

### 结论

`APIWorker` 应被拆分成多个更专注的服务。

## 2.3 抓取、解析、持久化边界不清

当前链路中存在明显的层次耦合：

- 解析器知道太多落库形态
- 数据库层承担了业务判断
- worker 层承担了流程编排和数据修补

例如：

- MySQL 更新逻辑中，不只是执行更新，还负责控制哪些字段是否写入
- Neo4j 更新逻辑中，也承担了“保留计数器/保留在线时长”的业务策略
- 解析器直接构建最终数据库需要的对象，而不是更纯粹的领域对象

### 结论

当前系统缺少稳定的层次边界：

- source adapter 层
- canonical domain 层
- application service 层
- repository 层

## 2.4 命名偏技术实现，不利于长期维护

当前命名如：

- `APIWorker`
- `SnapshotScanner`
- `MySQLManager`
- `Neo4jManager`

这些名称在项目早期没有问题，但随着复杂度上升，名称不能准确体现业务角色。

例如：

- `APIWorker` 实际不是简单“worker”，而是“节点详情抓取与同步编排器”
- `MySQLManager` 并不是通用 manager，而更像节点仓储与 ODS 写入仓储

### 结论

如果后续继续扩展，建议逐步将命名向“业务角色 + 技术边界”演进。

## 2.5 当前架构对 AllStarLink 专有字段耦合太深

当前解析逻辑高度依赖如下字段结构：

- `stats.user_node`
- `stats.data`
- `stats.data.nodes`
- `stats.data.linkedNodes`
- `server.SiteName`
- `server.Server_Name`

这些字段名和结构都属于 AllStarLink 的数据契约。

如果未来新增其他网站来源，当前代码中最难复用的是：

- `NodeParser`
- `APIWorker`
- 部分 MySQL / Neo4j 更新流程

因为整个流程默认了：

- 数据长什么样
- 主节点和子节点怎么拆
- 节点类型怎么推断
- 关系方向怎么推断

### 结论

必须引入 source adapter 层，把“不同站点的数据结构差异”隔离掉。

## 2.6 缺少“数据完整度状态”的显式建模

当前系统允许“先创建子节点占位数据，再等待它自己被完整抓取”，这个策略本身没有问题。

问题在于，这个状态没有显式字段标识。

当前主要依赖：

- `connections is None`
- `total_keyups is None`
- `total_tx_time is None`

来隐式表达“这个节点只是占位数据，还不是完整主节点”。

这会带来几个问题：

- 查询时不易区分
- 调试时不直观
- 将来换数据源时逻辑不统一

### 结论

占位状态和完整状态应该成为明确的数据状态，而不是隐式约定。

## 3. 为什么在接入其他网站前就应该重构

如果现在不重构，而是直接继续加第二个数据源，最可能出现的情况是：

1. 复制一份 `NodeParser`
2. 复制一份 `APIWorker`
3. 在 `Node` 模型上继续加字段
4. 在数据库更新逻辑里继续加 `if source == xxx`
5. 最后形成一套越来越难维护的“条件分支式架构”

短期看开发速度快，长期看会产生严重问题：

- 同类逻辑复制
- 模块间高耦合
- Bug 修复要改多处
- 一个数据源的变动可能影响另一个数据源
- 新人难以上手

### 结论

如果后续目标是“统一处理流程，接入多个站点”，那么现在正是最适合重构的时间点。

原因是：

- 当前主要数据源还只有 AllStarLink
- 复杂度尚可控制
- 重构成本远低于多数据源接入之后

## 4. 重构目标

这次重构不应该追求“漂亮架构”，而应该追求以下具体结果：

1. 数据源差异可隔离
2. 主流程可复用
3. 领域模型职责清晰
4. 数据库存储对象清晰
5. 新增站点时尽量新增代码，而不是修改旧主流程

## 5. 建议的目标架构

建议将当前结构演进为以下层次：

```text
src/link_scraper/
├─ app/                     # 应用编排层
├─ domain/                  # 领域模型
├─ sources/                 # 各数据源适配层
├─ repositories/            # 持久化仓储层
├─ services/                # 业务服务层
├─ pipelines/               # 抓取与同步流程
├─ task_queue/              # 队列与调度
├─ config/                  # 配置
└─ utils/                   # 通用工具
```

## 5.1 Source Adapter 层

建议新增：

```text
sources/
├─ base.py
└─ allstarlink/
   ├─ client.py
   ├─ parser.py
   └─ mapper.py
```

职责划分：

- `client.py`
  负责请求外部 API

- `parser.py`
  负责解析该网站的原始 JSON

- `mapper.py`
  负责把原始结构映射到统一领域模型

这样新增第二个网站时，可以新增：

```text
sources/other_site/
├─ client.py
├─ parser.py
└─ mapper.py
```

而不用改主流程。

## 5.2 统一领域模型层

建议把现在的 `Node` 拆成至少三类对象。

### 5.2.1 原始数据 DTO

按站点定义，例如：

- `AllStarLinkNodeDetailRaw`
- `AllStarLinkLinkedNodeRaw`

作用：

- 原样承接外部数据
- 不承担数据库含义

### 5.2.2 Canonical 领域模型

建议新增统一模型，例如：

- `CanonicalNode`
- `CanonicalConnection`
- `CanonicalNodeSnapshot`

作用：

- 统一各站点最终进入系统内部的语义
- 不绑定特定数据库实现

### 5.2.3 持久化对象

建议按存储目标拆分，例如：

- `GraphNodeRecord`
- `GraphConnectionRecord`
- `DimNodeRecord`
- `OdsNodeDetailRecord`

作用：

- 明确每个存储目标真正需要哪些字段
- 避免一个全能对象同时服务多个库

## 5.3 应用服务层

建议拆分出以下服务：

### `NodeFetchService`

负责：

- 按节点 ID 请求详情
- 重试
- 错误处理

### `NodeParseService`

负责：

- 解析主节点
- 解析子节点
- 解析关系

### `NodeSyncService`

负责：

- 协调图写入和关系写入
- 处理主节点和子节点写入顺序

### `OdsWriteService`

负责：

- 构建并写入 ODS 快照

### `BatchContextService`

负责：

- 批次号获取
- 批次号注入

## 5.4 仓储层

当前 `mysql_manager.py` 和 `neo4j_manager.py` 建议逐步重构为仓储层：

- `NodeGraphRepository`
- `TopologyRepository`
- `DimNodeRepository`
- `OdsNodeDetailRepository`

这些类只做一件事：

- 接收明确的持久化对象
- 执行数据库写入

不再在仓储内部承担业务判断。

## 6. 推荐的重构方向

## 6.1 第一优先级：引入 source adapter 抽象

这是最关键的第一步。

如果不先抽 source adapter，后面所有模型拆分都仍然会被 AllStarLink 耦合牵着走。

建议先定义一组最小接口：

```python
class SourceClient(Protocol):
    async def fetch_node_list(self) -> list: ...
    async def fetch_node_detail(self, node_id: str) -> dict: ...

class SourceMapper(Protocol):
    def map_node_list(self, payload: dict) -> list[NodeTask]: ...
    def map_node_detail(self, payload: dict) -> CanonicalNodeBundle: ...
```

这样主流程只依赖接口，不依赖 AllStarLink 字段结构。

## 6.2 第二优先级：拆掉全能 `Node`

建议先把 `Node` 从“数据库对象”降级为“统一领域对象”。

然后通过 mapper 转成：

- Neo4j record
- MySQL dim record
- ODS detail record

这样一来：

- 一个存储层改字段，不会直接污染领域模型
- 一个数据源加字段，不会强迫所有存储层一起加

## 6.3 第三优先级：瘦身 `APIWorker`

目标不是删除 `APIWorker`，而是让它只承担：

- 从队列取任务
- 调用统一处理流程
- 记录结果

理想状态下，它应该更像：

```python
node_id = await queue.dequeue()
bundle = await fetch_service.fetch(node_id)
canonical = parse_service.parse(bundle)
await sync_service.sync(canonical)
```

## 6.4 第四优先级：显式建模节点完整度

建议新增字段，例如：

- `record_kind = stub | full`
- `source_name = allstarlink | xxx`
- `data_completeness = partial | complete`

这样查询和调试时不用再通过空值猜状态。

## 7. 是否建议推倒重写

不建议推倒重写。

原因：

- 当前代码已经有可工作的主流程
- Redis 队列、批次号、限流、数据库写入机制都可以保留
- 真正需要重构的是模块边界和职责划分，不是把业务重做一遍

### 正确策略

应采用“平滑迁移式重构”：

1. 先抽接口
2. 再迁出实现
3. 最后替换主流程依赖

## 8. 分阶段重构计划

建议分四期进行。

## 第一期：建立可扩展边界

目标：

- 不改功能
- 先建立 source adapter 和 canonical model

建议动作：

1. 新建 `sources/base.py`
2. 新建 `sources/allstarlink/`
3. 把请求代码从 `APIWorker` 移到 `allstarlink/client.py`
4. 把解析代码从 `NodeParser` 移到 `allstarlink/parser.py`
5. 定义统一 `CanonicalNodeBundle`

交付结果：

- 主流程开始依赖抽象接口
- AllStarLink 成为第一套实现

## 第二期：拆分领域模型与持久化模型

目标：

- 降低 `Node` 模型复杂度

建议动作：

1. 新建 `domain/models.py`
2. 新建 `repositories/records.py`
3. 将当前 `Node` 中仅用于数据库的字段移出
4. 将 Neo4j / MySQL 的 record 组装逻辑从数据库层提出来

交付结果：

- 统一领域模型更加稳定
- 数据库存储结构不再污染主模型

## 第三期：瘦身流程编排类

目标：

- 拆解 `APIWorker`

建议动作：

1. 新建 `services/fetch_service.py`
2. 新建 `services/parse_service.py`
3. 新建 `services/sync_service.py`
4. 新建 `services/ods_service.py`
5. 把 `APIWorker` 改成轻量 orchestration worker

交付结果：

- 类变小
- 单元测试容易写
- 流程更可读

## 第四期：支持多数据源

目标：

- 在不改主流程的前提下接入第二个站点

建议动作：

1. 新增 `sources/other_source/`
2. 实现相同接口
3. 通过配置切换数据源
4. 验证统一流程可复用

交付结果：

- 真正形成可扩展抓取框架

## 9. 下次重构时的具体执行建议

为了避免一次改动过大，建议实际执行时遵循以下原则：

### 原则 1：保持现有输出不变

重构第一阶段不要同时改数据库字段和图结构。

先保证：

- Neo4j 结果不变
- MySQL 结果不变
- Redis 队列行为不变

这样才能安全替换内部结构。

### 原则 2：先抽象，再迁移

不要一边改主流程一边改所有实现。

建议：

1. 先定义接口
2. 再让老代码实现接口
3. 最后替换调用方

### 原则 3：先解决耦合，再解决命名

命名优化很重要，但不是第一优先级。

第一优先级是：

- 降低模型耦合
- 降低流程耦合
- 降低数据源耦合

命名可以在边界稳定后再统一调整。

## 10. 推荐的下一次重构起点

如果下一次真的开始做，建议从这里切入：

1. 新建 `sources/allstarlink/client.py`
2. 把 `_fetch_node_data()` 移过去
3. 新建 `sources/allstarlink/parser.py`
4. 把 `parse_node()` / `parse_linked_node()` / `parse_connections()` 移过去
5. 保持 `APIWorker` 先只改调用方式，不改业务流程

这是最稳妥的第一步，因为：

- 风险最小
- 收益最大
- 为后续多站点接入打下基础

## 11. 最终结论

当前代码：

- 可以继续维护
- 适合做小范围功能修补
- 不适合继续无重构地扩展到多数据源

如果后续计划复用现有流程抓取其他网站数据，那么应先做一次面向“多数据源适配”的结构化重构。

这次重构的核心不是“把代码写得更漂亮”，而是：

- 让数据源差异隔离
- 让流程可复用
- 让模型职责更清晰
- 让数据库层回归仓储角色

下一次正式重构时，应以本文档作为设计起点，而不是直接在现有代码上继续叠功能。

