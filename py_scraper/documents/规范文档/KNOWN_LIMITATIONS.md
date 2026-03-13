# 当前已知限制

本文档记录当前 `src/link_scraper` 版本已知的限制、折中设计和暂未处理的问题。

用途：

- 下次协作前快速恢复上下文
- 避免重复排查已经确认的问题
- 区分“已知限制”和“新引入缺陷”

## 1. 架构层限制

### 1.1 当前代码仍然是单数据源优先设计

虽然已经规划了多数据源重构方案，但当前主流程仍然是围绕 AllStarLink 数据结构组织的。

表现：

- 解析逻辑高度依赖 `stats.user_node`、`stats.data`、`linkedNodes`、`nodes`
- 主流程还没有 source adapter 抽象
- 接入其他网站时无法直接复用现有解析层

影响：

- 不适合继续无重构地扩展多个网站

### 1.2 领域模型尚未完成拆分

当前 `Node` 仍然承担了较多职责：

- 领域对象
- Neo4j 节点属性对象
- MySQL 节点状态对象
- 占位子节点载体

影响：

- 字段较多
- 可读性一般
- 多存储目标之间耦合较高

## 2. 流程层限制

### 2.1 `APIWorker` 仍然偏重

当前 `APIWorker` 仍承担：

- 任务消费
- 请求
- 重试
- 解析编排
- 图写入
- MySQL 写入
- ODS 写入

虽然已经做了一些局部修正，但整体仍偏“大类”。

影响：

- 维护成本较高
- 后续重构时应优先瘦身

### 2.2 主调度依赖“队列清空后再触发新扫描”

当前 `main.py` 的调度策略不是严格定时全量扫描，而是：

1. 队列为空
2. 触发新一轮 `SnapshotScanner`
3. 等待一段时间后继续

影响：

- 这是一种业务调度策略，不是通用采集框架策略
- 后续如果接入其他网站，可能要重新抽象调度层

## 3. 数据层限制

### 3.1 子节点存在占位状态

当前图模型允许：

- 子节点先作为占位节点进入图
- 后续再由该节点自身详情抓取补全统计字段

当前已做的修正：

- 子节点缺失统计值时不再写伪 `0`
- 改为写 `None/null`

当前仍然存在的限制：

- 占位状态没有显式状态字段
- 仍然需要通过空值判断“是否为完整节点”

### 3.2 Neo4j 采用按批次实例化节点

当前 `unique_id` 规则：

```text
{node_id}_{batch_no}
```

这意味着：

- 同一业务节点在不同批次中会生成多个图节点实例

优点：

- 可保留批次快照

限制：

- 图中会存在多个历史实例
- 查询时必须明确批次条件

### 3.3 `dim_nodes` 更新仍然偏保守

当前 `dim_nodes` 更新逻辑只更新部分字段，且有选择性覆盖策略。

表现：

- 子节点更新不覆盖 `current_link_count`
- 子节点缺失 `apprptuptime` 时不覆盖原值
- 并非所有模型字段都会落到 `dim_nodes`

影响：

- 代码中的字段定义与真实入库字段并不完全一致
- 阅读时必须以实际 SQL 为准

### 3.4 `ods_nodes_details.links` 为 JSON 列，但语义上存字符串

当前约定：

- `links` 字段的业务来源是 `stats.data.nodes`
- 该来源本质上是字符串
- 由于数据库列是 JSON 类型，写库前会做 `json.dumps()`

影响：

- 数据库里保存的是 JSON 字符串值，不是 JSON 数组
- 读取时需要清楚这一点

## 4. 文档层限制

### 4.1 历史文档已失效

`documents` 目录下部分旧文档与当前代码不一致，尤其是旧表结构说明、旧流程说明。

当前有效文档应优先参考：

- `README_LINK_SCRAPER_ARCHITECTURE.md`
- `README_LINK_SCRAPER_MODELS.md`
- `README_LINK_SCRAPER_REFACTOR_PLAN.md`
- `README_LINK_SCRAPER_REFACTOR_TASKS.md`
- `README_LINK_SCRAPER_REFACTOR_CHECKLIST.md`
- `README_LINK_SCRAPER_REFACTOR_ISSUES.md`

### 4.2 终端存在中文编码显示问题

部分文件在当前终端输出时会出现乱码，但这不等于文件本身逻辑无效。

影响：

- 终端阅读体验较差
- 修改时应以实际文件内容和结构为准，不要只依赖终端显示

## 5. 当前已确认的设计结论

以下结论在后续协作中应默认成立，除非明确修改：

1. `src/link_scraper` 是当前主线代码
2. 历史 `documents` 中旧表结构说明不作为最终依据
3. 以当前源码行为为准判断真实数据流
4. 子节点缺失统计数据时应写 `null`，不应写伪 `0`
5. `SnapshotScanner._cleanup_offline_nodes()` 已废弃并删除
6. `ods_nodes_details.links` 记录 `stats.data.nodes`，写库前转成合法 JSON 字符串

## 6. 后续优先处理项

如果后续继续演进，优先建议处理：

1. source adapter 抽象
2. `Node` 模型拆分
3. `APIWorker` 瘦身
4. repository 层收敛
5. 占位节点状态显式建模

