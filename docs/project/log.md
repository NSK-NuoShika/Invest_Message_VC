# 日志规范

程序日志文件位于项目根目录 `log/` 下，不输出到终端。

## `larkbot.log` —— 与上游的往来

负责：接收 LarkBot 派发的用户命令、向上游注册与心跳、向用户发送文字或文件的记录。

字段：

- `RECEIVE` 行：`ISO8601时间 事件 上游url 用户id HTTP状态 业务状态码`
- `SEND` 行：`ISO8601时间 事件 上游url 类型 用户id HTTP状态 业务状态码`
- `REGISTER` 行：`ISO8601时间 事件 上游url 程序名 接口名 接口路径 程序url HTTP状态 业务状态码`
- `HEARTBEAT` 行：`ISO8601时间 事件 上游url HTTP状态 业务状态码`

超时的 `SEND` 行省略第二个状态码：`ISO8601时间 事件 上游url 类型 用户id TIMEOUT`。

- 事件四种：`RECEIVE` 收到派发 / `SEND` 发送给用户 / `REGISTER` 注册 / `HEARTBEAT` 心跳
- 类型取值：`TEXT`/`FILE`
- 接口路径以 `/` 开头、不含域名，如 `/query`
- `RECEIVE` 时为 LarkBot 派发到本程序的地址，例如 `http://127.0.0.1:9001`；其余为被调用的 LarkBot 接口完整地址（含接口路径）
- 若请求上游接口超时时，将两个状态码替换为单个 `TIMEOUT`，其他字段不变。

### 示例

```text
2026-11-11T09:00:00 REGISTER http://127.0.0.1:8000/register 基金 查询 /query http://127.0.0.1:9001 200 0
2026-11-11T09:00:10 HEARTBEAT http://127.0.0.1:8000/heartbeat 200 0
2026-11-11T09:30:00 RECEIVE http://127.0.0.1:9001/query ou_55e1a0c9 200 0
2026-11-11T09:30:02 SEND http://127.0.0.1:8000/send/file FILE ou_55e1a0c9 200 0
2026-11-11T09:31:05 SEND http://127.0.0.1:8000/send/text TEXT ou_7a2c4f31 TIMEOUT
```

## `schedule.log` —— 定时任务

负责：定时任务的设置与触发记录。

字段：

- `ADD` 行：`ISO8601时间 事件 用户id 计划时间`
- `DEL` 行：`ISO8601时间 事件 用户id 计划时间`
- `TRIGGER` 行：`ISO8601时间 事件 用户id 计划时间`

- 事件三种：`ADD` 添加 / `DEL` 删除 / `TRIGGER` 触发
- 计划时间格式为 `HH:MM`，如 `09:30`。

### 示例

```text
2026-11-11T09:45:30 ADD ou_55e1a0c9 09:30
2026-11-11T10:02:44 DEL ou_55e1a0c9 09:30
2026-11-11T21:00:00 TRIGGER ou_55e1a0c9 21:00
```

## `task.log` —— 取数与 PDF

负责：基金基金数据查询与 PDF 生成的记录。

字段：

- `FETCH` 行：`ISO8601时间 事件 基金代码 耗时毫秒 结果`
- `PDF` 行：`ISO8601时间 事件 字节数 耗时毫秒 结果`

- 事件两种：`FETCH` 查询基金数据 / `PDF` 生成 PDF
- 结果取值：`OK` 成功 / `FAIL` 失败

### 示例

```text
2026-11-11T09:30:00 FETCH 000001 717 OK
2026-11-11T09:30:02 FETCH 161725 653 FAIL
2026-11-11T09:30:03 PDF 42593 250 OK
```
