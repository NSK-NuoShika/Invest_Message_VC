"""程序入口。"""

from __future__ import annotations

from src.command import api
from src.database import db
from src.larkbot import worker
from src.scheduler import jobs, rebuild
from src.service import query


def main() -> None:

    db.init_db()
    worker.register_all()
    worker.start_heartbeat()
    jobs.start(lambda user_id: query.handle_query(user_id, ["今天"]))
    rebuild.rebuild()
    api.start()


if __name__ == "__main__":
    main()
