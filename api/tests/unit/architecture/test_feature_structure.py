from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3] / "app"


def test_models_and_repositories_are_feature_local() -> None:
    assert not (APP_DIR / "models").exists()
    assert not (APP_DIR / "repositories").exists()


def test_app_code_does_not_import_top_level_models_or_repositories() -> None:
    forbidden_imports = (
        "app.models",
        "app.repositories",
        "..models",
        "..repositories",
    )
    offenders: list[tuple[str, str]] = []

    for path in APP_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text()
        for forbidden_import in forbidden_imports:
            if forbidden_import in text:
                offenders.append((str(path.relative_to(APP_DIR)), forbidden_import))

    assert offenders == []
