"""AllStarLink 模块包。

包初始化阶段不主动导入 `module.py`，避免数据库层引用 record 模型时
过早触发 app/bootstrap 相关依赖，造成循环导入。
"""

__all__: list[str] = []
