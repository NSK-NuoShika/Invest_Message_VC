# 程序架构

本文件为 `Invest_Message` 的架构文档，规定了模块划分、目录结构与各文件职责。

## 二、目录结构

```text
Invest_Message/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── log/
│   │   ├── __init__.py
│   │   ├── larkbot_log.py
│   │   ├── schedule_log.py
│   │   └── task_log.py
│   ├── command/
│   │   ├── __init__.py
│   │   └── api.py
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── jobs.py
│   │   └── rebuild.py
│   ├── service/
│   │   ├── __init__.py
│   │   ├── route.py
│   │   ├── help.py
│   │   ├── query.py
│   │   ├── watchlist_query.py
│   │   ├── watchlist_add.py
│   │   ├── watchlist_delete.py
│   │   ├── schedule_query.py
│   │   ├── schedule_add.py
│   │   └── schedule_delete.py
│   ├── model/
│   │   ├── __init__.py
│   │   └── fund.py
│   ├── fund/
│   │   ├── __init__.py
│   │   └── fetcher.py
│   ├── pdf/
│   │   ├── __init__.py
│   │   ├── renderer.py
│   │   └── fonts.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── db.py
│   └── larkbot/
│       ├── __init__.py
│       ├── send.py
│       └── worker.py
│
├── main.py
│
├── tests/
│
├── docs/
│   └── project/
│       ├── architecture.md
│       ├── database.md
│       └── log.md
│
├── data/
├── log/
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── THIRD_PARTY_NOTICES.md
```

## 三、依赖方向

```text
command
└── service
    ├── database
    ├── fund
    ├── pdf
    ├── scheduler
    │   └── database
    └── larkbot

config
log
```

## 四、各包与各模块职责

### `src/config` —— 配置

读取项目根目录的 `.env`，提供全局唯一的配置对象。缺失时使用默认值，值非法时启动失败。监听 `127.0.0.1` 地址、数据库路径、日志目录是固定值，不通过配置修改。

- `settings.py` —— 读取 `.env`、类型转换、合法性校验、构造配置对象。

### `src/log` —— 日志

写日志记录，提供单例供所有包调用。

- `__init__.py` —— 三个日志单例导出。
- `larkbot_log.py` —— 写 `log/larkbot.log`。
- `schedule_log.py` —— 写 `log/schedule.log`。
- `task_log.py` —— 写 `log/task.log`。

### `src/command` —— 命令

启动 HTTP 服务。启动 Flask、校验 HTTP 参数，按接口调用对应的 service 函数。不发送消息，不碰数据库，不碰调度器，不含业务规则。

- `api.py` —— 启动 Flask；校验请求是否合法。

### `src/scheduler` —— 定时调度

持有进程内的定时任务表，负责任务的增加、删除与到点触发。

- `jobs.py` —— 持有调度器实例；任务的增加与删除，调用注入的回调。
- `rebuild.py` —— 启动时从数据库读取全部定时记录并逐条建任务。

### `src/service` —— 业务

业务编排，每条命令对应一个模块。校验业务参数，执行业务流程，生成结果后通过 larkbot 包发给用户。

- `route.py` —— 二级命令的识别与分派，按 `args[0]` 调用对应的处理函数。
- `help.py` —— `基金 帮助`：返回帮助文本。
- `query.py` —— `基金 查询`：读取自选或指定代码，逐只取数，调用 PDF 渲染和发送；同时作为定时到点的推送入口被注入调度器。
- `watchlist_query.py` —— `基金 自选 查询`：读取自选列表，返回。
- `watchlist_add.py` —— `基金 自选 添加`：校验六位数字与存在性，写库。
- `watchlist_delete.py` —— `基金 自选 删除 <代码>`：校验六位数字，删库。
- `schedule_query.py` —— `基金 定时 查询`：读取该用户全部时间点，返回。
- `schedule_add.py` —— `基金 定时 添加`：校验时间，写库，建调度任务。
- `schedule_delete.py` —— `基金 定时 删除`：校验时间，删库，删调度任务。

### `src/fund` —— 基金

调用 akshare。按调用方给出的条数，取回该基金最近的净值记录。

- `fetcher.py` —— 调用 akshare 取数据；返回最近 N 条净值记录，按日期升序，不足 N 条时返回已有的全部。

### `src/pdf` —— PDF

把 service 传入的结构化数据渲染成 PDF，返回字节流。

- `renderer.py` —— 按传入参数排版并输出 PDF。
- `fonts.py` —— 注册字体。

### `src/database` —— 数据库

数据库增删改查。

- `connection.py` —— 建立并配置连接。
- `db.py` —— 数据库增删改查。

### `src/larkbot` —— 与上游交互

向上游发送文字与文件，负责启动时的注册与常驻心跳。

- `send.py` —— 发送文字消息与文件消息。
- `worker.py` —— 注册和心跳。

## 五、`main.py`

程序入口。