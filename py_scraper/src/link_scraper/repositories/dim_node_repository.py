"""
维表仓储。
"""

import logging
from typing import TYPE_CHECKING

from .records import DimNodeRecord

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..database.mysql_manager import MySQLManager


class DimNodeRepository:
    """封装 dim_nodes 的写入语义。"""

    def __init__(self, mysql_manager: "MySQLManager") -> None:
        self.mysql_manager = mysql_manager

    async def update_node(
        self,
        node: DimNodeRecord,
        update_current_link_count: bool = True,
    ) -> None:
        await self.mysql_manager.updateSingleNode(
            node,
            update_current_link_count=update_current_link_count,
        )
