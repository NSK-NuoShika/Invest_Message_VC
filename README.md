# Invest_Message

飞书机器人中间层（LarkBot）的下游程序：接收用户命令，维护自选基金与定时，渲染基金 PDF，并通过 LarkBot 发送给用户。

## 功能

- `基金 帮助`：回复全部可用命令。
- `基金 查询 <区间词…>`：查询自选基金，回复 PDF。
- `基金 查询 <代码> <区间词…>`：查询指定基金，回复 PDF。
- `基金 自选 查询 / 添加 <代码> / 删除 <代码>`：维护自选。
- `基金 定时 查询 / 添加 <HH:MM> / 删除 <HH:MM>`：维护每日推送时间点。
- 区间词：`今天`、`7天`、`30天`、`1年`、`3年`、`5年`。

## 启动

创建环境，安装依赖：

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate.bat
# Linux
source .venv/bin/activate

pip install -r requirements.txt
```

复制示例文件 `.env.example` 为 `.env` 后按需修改：

## 启动

先确保上游 LarkBot 已在运行，再启动本程序：

```bash
python src/main.py
```

## 许可

本项目使用 MIT 许可证；第三方依赖及其许可证原文见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
