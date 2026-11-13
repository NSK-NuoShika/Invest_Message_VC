"""启动时依据数据库全量重建任务表。"""

from __future__ import annotations

from src.database import db
from src.scheduler import jobs


def rebuild() -> None:
    """从数据库读取全部定时记录，逐条建立调度任务。"""

    for user_id, hhmm in db.list_all_schedules():
        jobs.add(user_id, hhmm)
