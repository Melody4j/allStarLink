# 新版爬虫数据模型说明

本文档以 `src/link_scraper` 当前代码为准，聚焦新版爬虫中的领域模型定义，以及 Neo4j / MySQL 的当前使用方式。

## 1. 领域模型总览

当前核心领域模型有三类：

- `Node`
- `Connection`
- `OdsNodeDetail`

对应文件：

- `src/link_scraper/models/node.py`
- `src/link_scraper/models/connection.py`
- `src/link_scraper/models/ods_node_detail.py`

## 2. Node 模型

文件：

- `src/link_scraper/models/node.py`

`Node` 表示一个业务节点，也对应 Neo4j 中的 `Node` 标签节点。

### 2.1 核心字段

- `node_id`: 节点 ID
- `callsign`: 呼号
- `node_type`: 平台类型，当前一般为 `allstarlink`
- `lat`, `lon`: 经纬度
- `apprptuptime`: 在线时长
- `total_keyups`: 总 keyup 次数
- `total_tx_time`: 总发射时长
- `last_seen`: 最后一次抓取时间
- `active`: 是否活跃
- `updated_at`: 更新时间
- `node_rank`: 节点类型标签，如 `Hub` / `Repeater`
- `features`: 特征列表
- `tone`: tone 数值
- `location_desc`: 从 `node_tone` 推导出的业务描述
- `hardware_type`: 硬件类型
- `connections`: 连接数
- `batch_no`: 当前批次号
- `unique_id`: 节点唯一标识

### 2.2 扩展字段

- `owner`
- `affiliation`
- `site_name`
- `affiliation_type`
- `country`
- `continent`
- `mobility_type`
- `first_seen_at`
- `is_mobile`
- `app_version`
- `is_bridge`
- `access_webtransceiver`
- `ip_address`
- `timezone_offset`
- `is_nnx`
- `history_total_keyups`
- `history_tx_time`
- `access_telephoneportal`
- `access_functionlist`
- `access_reverseautopatch`
- `seqno`
- `timeout`
- `totalexecdcommands`

### 2.3 主节点与子节点的差异

#### 主节点

由 `NodeParser.parse_node()` 生成，具备真实统计字段：

- `apprptuptime`
- `total_keyups`
- `total_tx_time`
- `connections`

#### 子节点

由 `NodeParser.parse_linked_node()` 生成。

当前代码策略是：

- 如果 API 不提供完整统计信息，则这些字段设为 `None`
- 不再用 `0` 作为伪默认值

也就是说，子节点占位数据中，以下字段可能为空：

- `apprptuptime`
- `total_keyups`
- `total_tx_time`
- `connections`

这表示“当前未知”，而不是“真实为 0”。

### 2.4 校验规则

`Node.validate()` 当前要求：

- `node_id` 必须存在
- 经纬度必须合法
- `last_seen <= updated_at`
- `total_keyups` 如果不为空，不能小于 0
- `total_tx_time` 如果不为空，不能小于 0

## 3. Connection 模型

文件：

- `src/link_scraper/models/connection.py`

`Connection` 表示节点之间的一条拓扑关系。

### 3.1 字段定义

- `source_id`
- `target_id`
- `status`
- `direction`
- `last_updated`
- `active`
- `batch_no`

### 3.2 status 取值

- `Active`
- `Inactive`

### 3.3 direction 取值

- `Transceive`
- `RX Only`
- `Local`
- `Permanent`
- `Unknown`

## 4. OdsNodeDetail 模型

文件：

- `src/link_scraper/models/ods_node_detail.py`

`OdsNodeDetail` 表示写入 `ods_nodes_details` 的一条节点详情快照。

### 4.1 核心字段

- `node_id`
- `node_type`
- `callsign`
- `frequency`
- `tone`
- `affiliation`
- `site_name`
- `is_active`
- `last_seen`
- `latitude`
- `longitude`
- `app_version`
- `ip`
- `timezone_offset`
- `is_nnx`
- `total_keyups`
- `total_tx_time`
- `access_webtransceiver`
- `access_telephoneportal`
- `access_functionlist`
- `access_reverseautopatch`
- `seqno`
- `timeout`
- `apprptuptime`
- `total_execd_commands`
- `max_uptime`
- `current_link_count`
- `linked_nodes`
- `links`
- `port`
- `batch_no`

### 4.2 JSON 字段说明

当前 ODS 模型中有两个复合结构字段：

- `linked_nodes`
- `links`

当前写库策略：

- `linked_nodes`: 保存 `stats.data.linkedNodes` 的 JSON 序列化结果
- `links`: 保存 `stats.data.nodes` 原始字符串，并在写库前用 `json.dumps()` 转成合法 JSON 字符串

这样可以兼容 MySQL 的 JSON 列要求。

## 5. Neo4j 模型

## 5.1 Node 标签

当前代码写入的节点标签：

- `Node`

### 5.1.1 当前写入的属性

- `unique_id`
- `node_id`
- `callsign`
- `node_type`
- `lat`
- `lon`
- `apprptuptime`
- `total_keyups`
- `total_tx_time`
- `last_seen`
- `active`
- `updated_at`
- `node_rank`
- `features`
- `tone`
- `location_desc`
- `hardware_type`
- `siteName`
- `connections`
- `batch_no`

### 5.1.2 唯一约束

当前唯一明确创建的约束：

- `:Node(unique_id)` 唯一约束

### 5.1.3 唯一标识规则

当前节点唯一标识是：

```text
unique_id = "{node_id}_{batch_no}"
```

这意味着同一节点在不同批次中会生成不同的图节点实例。

## 5.2 CONNECTED_TO 关系

当前关系标签：

- `CONNECTED_TO`

### 5.2.1 当前写入的属性

- `status`
- `direction`
- `last_updated`
- `active`
- `batch_no`

### 5.2.2 批次隔离

关系更新基于 `src_unique_id` 和 `dst_unique_id`，也就是同一批次内的节点实例。

因此当前拓扑图是按批次隔离的。

## 6. MySQL 模型

## 6.1 dim_nodes

当前代码对 `dim_nodes` 的使用方式：

- `SnapshotScanner` 批量更新在线节点连接数
- `APIWorker` 更新主节点和子节点的部分字段

### 6.1.1 当前明确写入的字段

- `node_id`
- `access_webtransceiver`
- `ip_address`
- `timezone_offset`
- `is_nnx`
- `history_total_keyups`
- `history_tx_time`
- `access_telephoneportal`
- `access_functionlist`
- `access_reverseautopatch`
- `seqno`
- `timeout`
- `totalexecdcommands`
- `apprptuptime`
- `site_name`
- `current_link_count`
- `node_type`
- `last_seen`
- `is_active`

### 6.1.2 当前写入规则

主节点更新：

- 会更新 `current_link_count`
- 会更新 `apprptuptime`

子节点更新：

- 不更新 `current_link_count`
- 如果 `apprptuptime` 为空，则不覆盖原值

## 6.2 ods_nodes_details

当前代码对 `ods_nodes_details` 的使用方式：

- 每成功抓取一个主节点详情，就插入一条快照记录

这是“只插入，不更新”的 ODS 明细表。

### 6.2.1 当前插入字段

- `node_id`
- `node_type`
- `callsign`
- `frequency`
- `tone`
- `affiliation`
- `site_name`
- `is_active`
- `last_seen`
- `latitude`
- `longitude`
- `app_version`
- `ip`
- `timezone_offset`
- `is_nnx`
- `total_keyups`
- `total_tx_time`
- `access_webtransceiver`
- `access_telephoneportal`
- `access_functionlist`
- `access_reverseautopatch`
- `seqno`
- `timeout`
- `apprptuptime`
- `total_execd_commands`
- `max_uptime`
- `current_link_count`
- `linked_nodes`
- `links`
- `port`
- `batch_no`

## 7. 当前模型设计的关键特点

### 7.1 批次化图模型

Neo4j 当前不是“单节点滚动更新”模型，而是“按批次实例化”的图模型：

- 同一个 `node_id`
- 在不同 `batch_no`
- 会生成不同 `unique_id`

优点：

- 可以保留批次快照
- 便于回放某一批次拓扑

代价：

- 图中会出现同一业务节点的多份实例

### 7.2 子节点先占位，后补全

当前代码允许：

1. 先通过别人 `linkedNodes` 把某节点创建出来
2. 再在该节点自己被抓取时补全真实统计值

因此查询图数据时，应区分：

- 占位子节点
- 已被完整抓取的主节点

### 7.3 MySQL 与 Neo4j 的分工

当前分工大致如下：

- Neo4j：拓扑关系、批次图结构
- `dim_nodes`：节点当前状态的部分字段
- `ods_nodes_details`：节点详情快照明细

