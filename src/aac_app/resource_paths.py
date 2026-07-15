from importlib.resources import files


def package_resource_path(relative_path: str) -> str:
    """Return absolute filesystem path for a resource inside the app package."""
    return str(files("app").joinpath(relative_path))
