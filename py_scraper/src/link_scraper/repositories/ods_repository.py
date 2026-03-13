"""
ODS 仓储。
"""

import logging
from typing import TYPE_CHECKING

from .records import OdsNodeDetailRecord

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..database.mysql_manager import MySQLManager


class OdsRepository:
    """封装 ods_nodes_details 的写入语义。"""

    def __init__(self, mysql_manager: "MySQLManager") -> None:
        self.mysql_manager = mysql_manager

    async def insert_detail(self, detail: OdsNodeDetailRecord) -> None:
        await self.mysql_manager.insert_ods_node_detail(detail)
