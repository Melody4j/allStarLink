"""OtherSource 模块包。

包初始化阶段不主动导入 `module.py`，避免 source factory 装配时产生循环依赖。
"""

__all__: list[str] = []
