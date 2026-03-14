# 数据源模块化 V3 调度设计

本文档同步当前调度层的实际落地状态。

## 1. 调度目标

调度层负责解决：

1. 统一启动多个 source module
2. 支持同一 source 下多个任务并存
3. 允许不同任务使用不同调度模式
4. 单任务失败不影响其他任务
5. 调度逻辑与业务逻辑分离

## 2. 当前核心对象

### 2.1 `AppContext`

当前承载：

1. `settings`
2. `redis_client`
3. `relational_storage_manager`
4. `graph_storage_manager`
5. `priority_queue`
6. `rate_limiter`
7. `batch_manager`

### 2.2 `SourceModule`

当前实现：

1. `AllStarLinkModule`
2. `OtherSourceModule`

职责：

1. 返回当前 source 的 jobs
2. 不自己维护额外调度器

### 2.3 `ScheduledJob`

当前协议：

1. `name`
2. `schedule_spec`
3. `start()`
4. `run_once()`
5. `shutdown()`

### 2.4 `ScheduleSpec`

当前字段：

1. `mode`
2. `interval_seconds`
3. `timeout_seconds`
4. `cooldown_seconds`
5. `max_consecutive_failures`

## 3. 当前支持的调度模式

### 3.1 `continuous`

适用任务：

1. `allstarlink.node_topology`

当前行为：

1. 由 scheduler 拉起
2. 异常退出后自动重启

### 3.2 `interval`

适用任务：

1. `allstarlink.node_list_snapshot`
2. `other_source.source_probe`

当前行为：

1. 按固定间隔执行 `run_once()`
2. 单轮失败只影响当前任务

### 3.3 `manual`

当前行为：

1. 允许注册
2. scheduler 默认不自动执行

## 4. 当前保护能力

### 4.1 失败隔离

已支持：

1. interval 任务失败不会拖垮其他任务
2. continuous 任务异常退出后会自动拉起

### 4.2 超时保护

已支持：

1. `timeout_seconds`
2. 超时会记入失败状态

### 4.3 失败冷却

已支持：

1. `cooldown_seconds`
2. 连续失败达到阈值后使用更长冷却时间

### 4.4 运行状态

已支持：

1. `last_started_at`
2. `last_finished_at`
3. `last_success_at`
4. `last_failure_at`
5. `next_run_at`
6. `consecutive_failures`
7. `is_running`
8. `last_error`

## 5. 当前装配链路

```text
main.py
-> app/bootstrap.py
-> load_modules(settings)
-> TaskRegistry
-> AppScheduler
-> jobs
```

当前已验证注册形态：

```text
AllStarLinkModule
-> allstarlink.node_topology
-> allstarlink.node_list_snapshot

OtherSourceModule
-> other_source.source_probe
```

## 6. 当前明确不做项

本轮不做：

1. 全局并发上限
2. source 级并发上限
3. task overlap / max_concurrency
4. 链式触发调度

## 7. 结论

当前调度层已经满足本轮 V3 重构目标：

1. 能统一装配多个 source module
2. 同一 source 下可并存多个任务
3. 不同任务可配置不同调度模式
4. 单任务失败不会影响其他任务
5. 任务运行状态可观测

测试命令：

```bash
python -m unittest discover -s tests
```

当前结果：

1. `32` 个测试通过
