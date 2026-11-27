import ast
from pathlib import Path


def test_services_have_no_http_dependency_or_direct_database_io():
    directory = Path(__file__).resolve().parents[1] / "app/services"
    for path in directory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("fastapi"), path.name
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
            ):
                assert node.func.attr not in {
                    "execute",
                    "scalar",
                    "scalars",
                    "add",
                    "add_all",
                    "delete",
                    "flush",
                    "commit",
                    "rollback",
                    "get",
                    "query",
                }, (path.name, node.lineno)


def test_repositories_do_not_import_http_schemas_or_services():
    directory = Path(__file__).resolve().parents[1] / "app/repositories"
    for path in directory.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(
                    ("fastapi", "app.services", "app.schemas"),
                ), path.name
