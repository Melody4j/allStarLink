# WIRES-X 数据源调研报告

更新时间：

- 2026-03-13

调研方式：

- 使用 Playwright 直接访问 Yaesu 官方 WIRES-X 公开页面
- 重点验证公开可爬字段、页面结构、更新频率、节点与房间关系、以及是否存在可直接获取的拓扑数据

## 1. 调研结论摘要

本次调研确认，WIRES-X 官方公开页面中可以稳定获取以下三类数据：

1. 活动节点列表
2. 活动房间列表
3. 各区域注册 ID 列表（节点 ID / 房间 ID 配对）

这些数据足以支持构建：

- 节点目录库
- 房间目录库
- Node -> Room 的注册映射
- 房间活跃度快照
- 节点 / 房间的地理分布分析

但目前没有在公开页面中发现以下数据：

- 当前某个节点正在连接哪个房间的结构化实时列表
- 当前某个房间下所有在线节点成员的结构化列表
- 节点与节点之间的实时邻接拓扑

因此，基于公开网页层面，WIRES-X 更适合建模为：

- 节点数据源
- 房间数据源
- Node -> Room 注册关系图
- Room 活跃度时序数据
- 评论字段中可抽取的弱关系

而不适合直接建成类似 AllStarLink 那种强实时 node-node 拓扑图。

## 2. 已确认的官方公开页面

### 2.1 活动节点列表

页面：

- [WIRES-X ACTIVE NODE ID list](https://www.yaesu.com/jp/en/wires-x/id/active_node.php)

页面特征：

- 公开可访问，无需登录
- 服务端返回 HTML 表格
- 页面标注 `Update every 20 min`
- Playwright 实测可直接读取表格

本次调研时的页面头部信息：

- `LATEST WIRES-X ACTIVE NODE ID LIST`
- `Update every 20 min 13 Mar 2026 11:11:21 GMT`

Playwright 实测结果：

- 总行数：3162
- 数据行数：3161

表头字段：

- `NODE ID`
- `DTMF ID`
- `Call Sign`
- `Ana/Dig`
- `City`
- `State`
- `Country`
- `Freq(MHz)`
- `SQL`
- `Lat`
- `Lon`
- `Comment`

### 2.2 活动房间列表

页面：

- [WIRES-X ACTIVE ROOM ID list](https://www.yaesu.com/jp/en/wires-x/id/active_room.php)

页面特征：

- 公开可访问，无需登录
- 服务端返回 HTML 表格
- 页面标注 `Update every 20 min`
- Playwright 实测可直接读取表格

本次调研时的页面头部信息：

- `LATEST WIRES-X ACTIVE ROOM ID LIST`
- `Update every 20 min 13 Mar 2026 11:11:22 GMT`

Playwright 实测结果：

- 总行数：1496
- 数据行数：1495

表头字段：

- `ROOM ID`
- `DTMF ID`
- `Act`
- `Room Name`
- `City`
- `State`
- `Country`
- `Comment`

### 2.3 各区域注册 ID 列表

已确认页面：

- [Europe, Africa](https://www.yaesu.com/jp/en/wires-x/id/id_eu.php)
- [USA, N/Mid/S. America](https://www.yaesu.com/jp/en/wires-x/id/id_usa.php)
- [Asia, Oceania](https://www.yaesu.com/jp/en/wires-x/id/id_asia.php)
- [Japan](https://www.yaesu.com/jp/en/wires-x/id/id_japan.php)

页面特征：

- 公开可访问，无需登录
- 服务端返回 HTML 表格
- 提供节点 DTMF ID 与房间 DTMF ID 的配对关系

典型表头：

- `DTMF NODE ID`
- `DTMF ROOM ID`
- `Call Sign`
- `City`
- `State`
- `Country`

## 3. 可爬取的数据范围

## 3.1 节点数据

基于 `active_node.php`，可直接抓取以下节点字段：

- 节点展示 ID：`NODE ID`
- 5 位接入 ID：`DTMF ID`
- 呼号：`Call Sign`
- 模式：`Ana/Dig`
- 城市：`City`
- 州 / 省 / 地区：`State`
- 国家：`Country`
- 频率：`Freq(MHz)`
- 静噪 / 数字组信息：`SQL`
- 纬度：`Lat`
- 经度：`Lon`
- 描述 / 备注：`Comment`

补充说明：

- `Ana/Dig` 可区分 `Analog`、`Digital`、`Digital(M)` 等模式
- 很多节点带有频率、经纬度和较长说明
- 说明字段中可能出现站点用途、开放性、是否常连某房间等信息

## 3.2 房间数据

基于 `active_room.php`，可直接抓取以下房间字段：

- 房间展示 ID：`ROOM ID`
- 5 位接入 ID：`DTMF ID`
- 活跃度：`Act`
- 房间名称：`Room Name`
- 城市：`City`
- 州 / 省 / 地区：`State`
- 国家：`Country`
- 描述 / 备注：`Comment`

补充说明：

- `Act` 字段可作为房间当前热度指标
- 房间说明中常包含用途、网络归属、桥接信息、站点说明
- 一些房间说明中还会出现跨协议桥接、固定中继、特定网络等信息

## 3.3 注册映射数据

基于 `id_*.php` 区域注册页面，可直接抓取：

- 节点 DTMF ID
- 房间 DTMF ID
- 呼号
- 地理归属

这组数据的最大价值在于：

- 可以形成稳定的 `Node -> Room` 注册映射关系
- 可以补足活动页之外的注册层数据
- 可以作为节点主档和房间主档的基础维表

## 4. 拓扑与关系建模结论

## 4.1 可以直接得到的强关系

### 关系 1：节点注册到房间

来源：

- 各区域 `id_*.php` 页面

可建模为：

```text
Node -(registered_room)-> Room
```

这是当前最稳定、最明确、最适合产品化的数据关系。

### 关系 2：房间当前活跃度

来源：

- `active_room.php` 中的 `Act`

可建模为：

```text
Room -(activity_snapshot)-> Metric
```

说明：

- 官方用户页说明房间列表可按活动数 / 连接节点数排序
- 因此 `Act` 很可能可视为房间当前连接活跃度指标
- 这里属于基于官方说明的合理推断，建议在产品文档中标记为“活跃度字段”

## 4.2 可以构建的弱关系

### 关系 3：节点说明中提及目标房间

部分节点评论字段中会出现类似文本：

- `Use room ID 24060 please`
- `Call 69437 AUCKLANDLINK`
- `... ROOM #20339D に常时接続`

这类信息可以做规则抽取，形成：

```text
Node -(comment_inferred_room)-> Room
```

注意：

- 这不是官方结构化关系
- 只适合做“推断边”
- 不能和注册映射边等同

## 4.3 当前无法直接得到的关系

本次调研中，没有在公开页面中发现以下结构化数据：

- 当前某个节点连接到哪个房间的实时结构化列表
- 当前某个房间下有哪些在线节点成员
- 节点与节点之间的实时连接图
- 类似 AllStarLink `linkedNodes` 的详情页或公开 API

因此当前不建议承诺以下产物：

- 实时 node-node 拓扑图
- 精确的 room 成员表
- 精确的“当前 node 正在连接哪个 room”的全量事实表

## 5. 官方业务语义确认

根据官方说明页，可以确认以下语义：

页面：

- [WIRES-X Opening a node](https://www.yaesu.com/jp/en/wires-x/node/index.php)
- [WIRES-X User page](https://www.yaesu.com/jp/en/wires-x/user/index.php)

确认点：

1. 用户先接入本地 node
2. 再通过本地 node 去连接目标 node 或 room
3. room 是一个可由多个节点接入的社区空间
4. 房间列表可按活动度 / 连接节点数量排序

这说明 WIRES-X 的公开数据更接近：

- 节点目录
- 房间目录
- 节点到房间的注册与接入体系

而不是公开实时拓扑网络。

## 6. 对爬虫设计的影响

## 6.1 抓取难度

抓取难度较低，原因：

- 页面为静态 HTML 表格
- 无需复杂前端交互
- 无需先登录
- 不依赖浏览器执行复杂脚本

说明：

- 本次调研使用 Playwright 主要是为了验证页面结构和可访问性
- 正式接入时，优先建议使用普通 HTTP 请求 + HTML 解析，而不是浏览器自动化

## 6.2 建议的数据源拆分

如果后续把 WIRES-X 作为新的 source adapter 接入，建议拆为以下子源：

1. `wiresx_active_nodes`
2. `wiresx_active_rooms`
3. `wiresx_registered_ids`

这样可以把“活动快照”和“注册主档”分离处理。

## 6.3 建议的抓取频率

建议：

- 活动节点列表：每 20 分钟或略低于 20 分钟
- 活动房间列表：每 20 分钟或略低于 20 分钟
- 注册 ID 列表：每日一次或每周一次

原因：

- 活动页本身声明每 20 分钟更新
- 注册 ID 列表变化频率明显低于活动列表

## 7. 建议的数据模型

## 7.1 节点主档

建议字段：

- `source_name`
- `node_id`
- `dtmf_node_id`
- `callsign`
- `mode`
- `city`
- `state`
- `country`
- `frequency_text`
- `sql_text`
- `latitude_raw`
- `longitude_raw`
- `comment`
- `last_seen_at`
- `snapshot_time`

## 7.2 房间主档

建议字段：

- `source_name`
- `room_id`
- `dtmf_room_id`
- `room_name`
- `city`
- `state`
- `country`
- `comment`
- `last_seen_at`
- `snapshot_time`

## 7.3 注册映射表

建议字段：

- `source_name`
- `dtmf_node_id`
- `dtmf_room_id`
- `callsign`
- `city`
- `state`
- `country`
- `effective_at`
- `snapshot_time`

## 7.4 房间活跃度快照表

建议字段：

- `source_name`
- `room_id`
- `dtmf_room_id`
- `activity_count`
- `snapshot_time`

## 7.5 推断关系表

建议字段：

- `source_name`
- `node_id`
- `target_room_id`
- `evidence_text`
- `inference_type`
- `confidence`
- `snapshot_time`

## 8. 产品侧可形成的能力

基于当前公开数据，比较适合形成以下能力：

1. WIRES-X 节点目录
2. WIRES-X 房间目录
3. Node -> Room 注册关系图
4. 房间热度排行榜
5. 节点 / 房间地理分布地图
6. 评论中弱关系抽取与推荐
7. 房间活跃度历史趋势分析

## 9. 当前限制与风险

1. 无法从公开网页直接获得实时 node-node 拓扑
2. 无法直接获得 room 成员清单
3. 评论字段中虽然可能包含关系线索，但格式不统一
4. 经纬度字段是文本格式，需要额外标准化
5. 部分页面记录量很大，抓取时需要注意增量策略与解析效率

## 10. 建议的接入结论

如果后续把 WIRES-X 接入当前采集框架，推荐定位为：

- 一个“目录 + 注册映射 + 活跃度快照”型数据源

不建议初期定位为：

- 一个“实时拓扑边关系”型数据源

更准确的接入目标应该是：

1. 先抓节点目录与房间目录
2. 再抓节点和房间的注册映射
3. 再沉淀房间活跃度时序
4. 最后再尝试从评论字段中抽取弱关系

如果后续发现登录后页面、客户端接口、或其他官方 API，再评估是否补做更强的拓扑建模。
