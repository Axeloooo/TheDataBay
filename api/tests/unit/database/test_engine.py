import app.database.engine as engine_module


def test_create_db_and_tables_imports_feature_models_before_create_all(monkeypatch):
    calls: list[tuple[str, object]] = []
    fake_engine = object()

    def fake_import_module(name: str):
        calls.append(("import", name))
        return object()

    def fake_create_all(*, bind):
        calls.append(("create_all", bind))

    monkeypatch.setattr(engine_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(engine_module, "get_engine", lambda: fake_engine)
    monkeypatch.setattr(engine_module.SQLModel.metadata, "create_all", fake_create_all)

    engine_module.create_db_and_tables()

    assert calls == [
        ("import", "app.agents.models"),
        ("import", "app.datasets.models"),
        ("create_all", fake_engine),
    ]
