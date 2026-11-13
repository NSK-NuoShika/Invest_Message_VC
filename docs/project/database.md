# 数据库约束

本文档规定 `Invest_Message` 程序的表结构、字段语义与写入规则。存储位置在项目根目录的 `data/invest_message.db`。

## 表 1：users —— 用户表

本表登记留下过数据的用户。

### 表结构

| 字段 | 类型 | 约束 | 存储内容 |
|---|---|---|---|
| `user_id` | TEXT | 主键 | 用户 id |

### 建表语句

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY
);
```

## 表 2：watchlist —— 自选表

本表登记用户关注的基金。

### 表结构

| 字段 | 类型 | 约束 | 存储内容 |
|---|---|---|---|
| `user_id` | TEXT | 非空，主键，外键，级联删除 | 归属用户的 id |
| `code` | TEXT | 非空，主键 | 6 位数字基金代码 |
| `name` | TEXT | 非空 | 基金名称 |

### 建表语句

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code    TEXT NOT NULL,
    name    TEXT NOT NULL,
    PRIMARY KEY (user_id, code)
);
```

## 表 3：schedules —— 定时表

本表登记用户的每日推送时间点。

### 表结构

| 字段 | 类型 | 约束 | 存储内容 |
|---|---|---|---|
| `user_id` | TEXT | 非空，主键，外键，级联删除 | 归属用户 id |
| `hhmm` | TEXT | 非空，主键 | 每日触发时刻，24 小时制 `HH:MM`，如 `09:30` |

### 建表语句

```sql
CREATE TABLE IF NOT EXISTS schedules (
    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    hhmm    TEXT NOT NULL,
    PRIMARY KEY (user_id, hhmm)
);
```
