from src import main as main_module


def test_main_order_and_scheduled_callback(monkeypatch) -> None:
    calls: list[object] = []
    callbacks: list[object] = []

    monkeypatch.setattr(main_module.db, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(
        main_module.jobs, "start", lambda callback: (calls.append("jobs.start"), callbacks.append(callback))
    )
    monkeypatch.setattr(main_module.rebuild, "rebuild", lambda: calls.append("rebuild"))
    monkeypatch.setattr(
        main_module.worker, "register_all", lambda: calls.append("register_all")
    )
    monkeypatch.setattr(
        main_module.worker, "start_heartbeat", lambda: calls.append("start_heartbeat")
    )
    monkeypatch.setattr(main_module.api, "start", lambda: calls.append("api.start"))
    monkeypatch.setattr(
        main_module.query,
        "handle_query",
        lambda user_id, args: calls.append(("query", user_id, args)),
    )

    main_module.main()

    assert calls == [
        "init_db",
        "register_all",
        "start_heartbeat",
        "jobs.start",
        "rebuild",
        "api.start",
    ]

    callback = callbacks[0]
    callback("ou_1")
    assert calls[-1] == ("query", "ou_1", ["今天"])
