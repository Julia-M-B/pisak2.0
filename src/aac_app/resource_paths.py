from importlib.resources import files


def package_resource_path(relative_path: str) -> str:
    """Return absolute filesystem path for a resource inside the aac_app package."""
    return str(files(__package__).joinpath(relative_path))
