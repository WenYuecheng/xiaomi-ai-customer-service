from importlib.util import find_spec


def test_application_package_exists() -> None:
    assert find_spec("app") is not None, "FastAPI application package has not been implemented"

