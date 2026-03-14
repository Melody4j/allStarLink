# 新版爬虫数据模型说明

本文档以当前 `src/link_scraper` 代码为准，描述重构后真实生效的数据模型分层。

## 1. 当前模型分层

当前模型已经分成三层：

1. 统一领域模型
2. 持久化 record 模型

## 2. 统一领域模型

文件：

- `src/link_scraper/domain/models.py`

### 3.1 `CanonicalNode`

作用：

- 表示 source 无关的统一节点语义
- 作为 source adapter 向系统内部传递的标准节点对象

特点：

- 不直接绑定 MySQL 或 Neo4j 的具体列结构
- 同时可表达主节点和子节点
- 子节点缺失统计值时保留 `None`

### 3.2 `CanonicalConnection`

作用：

- 表示统一的节点关系语义

当前关键字段语义：

- `source_id`
- `target_id`
- `direction`
- `status`
- `batch_no`

### 3.3 `CanonicalNodeBundle`

作用：

- 表示一次节点详情抓取得到的聚合结果

当前包含：

- 主节点
- 子节点列表
- 连接关系列表
- 原始 payload

说明：

`CanonicalNodeBundle` 是当前服务层和 mapper 层之间的核心交换对象。

## 3. 持久化 record 模型

文件：

- `src/link_scraper/repositories/records.py`

### 4.1 `GraphNodeRecord`

作用：

- Neo4j 节点写入对象

特点：

- 显式包含图节点写入所需字段
- 包含 `batch_no`
- 包含 `unique_id`

### 4.2 `GraphConnectionRecord`

作用：

- Neo4j `CONNECTED_TO` 关系写入对象

特点：

- 绑定 `src_unique_id` 与 `dst_unique_id`
- 关系隔离到具体批次

### 4.3 `DimNodeRecord`

作用：

- MySQL `dim_nodes` 更新对象

特点：

- 只保留维表更新真正需要的字段
- 子节点更新时可显式跳过部分字段覆盖

### 4.4 `OdsNodeDetailRecord`

作用：

- MySQL `ods_nodes_details` 插入对象

特点：

- 保存主节点详情快照
- 保留 `linked_nodes`
- 保留 `links`
- 包含 `batch_no`

## 4. 模型转换链路

当前主流程的数据转换链路是：

```text
AllStarLink payload
-> CanonicalNodeBundle
-> GraphNodeRecord / GraphConnectionRecord / DimNodeRecord / OdsNodeDetailRecord
-> Neo4j / MySQL
```

对应实现位置：

- source 映射：`src/link_scraper/sources/allstarlink/mapper.py`
- record 映射：`src/link_scraper/repositories/mappers.py`

## 5. 当前 Mapper 职责

### 6.1 Source Mapper

文件：

- `src/link_scraper/sources/allstarlink/mapper.py`

职责：

- 将 AllStarLink 列表接口映射为 `node_id + link_count`
- 将 AllStarLink 详情接口映射为 `CanonicalNodeBundle`

### 6.2 Repository Mapper

文件：

- `src/link_scraper/repositories/mappers.py`

当前主要 mapper：

- `GraphMapper`
- `DimNodeMapper`
- `OdsMapper`

职责：

- 将 `CanonicalNodeBundle` 或其中的 canonical 对象映射为各类存储 record

## 6. 当前关键建模约束

### 7.1 子节点统计缺失时必须写 `null`

当前已经明确采用以下策略：

- 子节点缺失统计字段时，保留 `None`
- 不再使用伪 `0`

这同时适用于 canonical model 和最终 record。

### 7.2 `ods_nodes_details.links` 的来源固定

当前 `links` 字段的业务来源固定为：

- `stats.data.nodes`

由于 MySQL 列类型是 JSON，写入前会做 JSON 序列化。

注意：

- 这里保存的是“JSON 字符串值”
- 不是解析后的 JSON 数组

### 7.3 Neo4j 仍然采用批次化节点实例

当前图节点唯一标识规则仍然是：

```text
unique_id = "{node_id}_{batch_no}"
```

因此：

- 同一业务节点在不同批次会产生不同图节点实例
- 关系同样按批次隔离

## 7. 当前仍未完成的建模项

虽然模型已经完成拆分，但还有两个建模项暂未推进：

1. 占位节点与完整节点的显式状态字段

也就是说，当前系统已经从“全能 Node”迁移出来，但尚未把“数据完整度状态”正式建模。
