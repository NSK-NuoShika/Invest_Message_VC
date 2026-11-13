"""持有进程内的定时任务表。"""

from __future__ import annotations

from typing import Callable

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from log import schedule_log

OnTrigger = Callable[[str], None]

_scheduler = BackgroundScheduler(
    executors={"default": {"type": "threadpool", "max_workers": 1}},
    job_defaults={"max_instances": 1, "coalesce": True},
)
_on_trigger: OnTrigger | None = None


def _job_id(user_id: str, hhmm: str) -> str:
    return f"{user_id}@{hhmm}"


def _fire(user_id: str, hhmm: str) -> None:
    """先记日志，再调用。"""
    schedule_log.trigger(user_id, hhmm)
    callback = _on_trigger
    if callback is not None:
        callback(user_id)


def start(on_trigger: OnTrigger) -> None:
    """注入到点回调并启动调度器。"""
    global _on_trigger
    _on_trigger = on_trigger
    if not _scheduler.running:
        _scheduler.start()


def add(user_id: str, hhmm: str) -> bool:
    """新增每日定时任务，幂等。"""
    job_id = _job_id(user_id, hhmm)
    if _scheduler.get_job(job_id) is not None:
        return False
    hour, minute = (int(part) for part in hhmm.split(":"))
    _scheduler.add_job(
        _fire,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[user_id, hhmm],
        id=job_id,
        name=job_id,
        replace_existing=True,
    )

    return True


def remove(user_id: str, hhmm: str) -> bool:
    """删除定时任务。"""
    try:
        _scheduler.remove_job(_job_id(user_id, hhmm))
    except JobLookupError:
        return False

    return True
