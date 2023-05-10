"""Modrinth API wrapper"""
from functools import cache

import requests


# Utils
def call_endpoint(endpoint: str, options: dict = None) -> dict | list[dict]:
    """
    Call an endpoint of the Modrinth API.
    :param endpoint: The endpoint to call.
    :param options: The options to pass to the endpoint.
    :return: The data returned by the endpoint.
    """
    r = requests.get(f"https://api.modrinth.com{endpoint}", params=options)
    return r.json()


# Functions
@cache
def search_mod(version: str, mod_loader: str, query: str):
    """
    Search for a mod on Modrinth.
    :param version: The Minecraft version to search the mod for.
    :param mod_loader: The mod loader to search the mod for.
    :param query: The query to search the mod.
    :return: The list of mods resulting from the search.
    """
    return call_endpoint("/v2/search", options={
        "facets": f"[[\"project_type:mod\"],[\"versions:{version}\"],[\"categories:{mod_loader}\"]]",
        "query": query
    })["hits"]


@cache
def get_files_for_mod(mod_id: str, version: str, mod_loader: int) -> list[list[dict]]:
    """
    Get the files for a mod.
    :param mod_id: The id/slug of the mod.
    :param version: The Minecraft version to search the mod for.
    :param mod_loader: The mod loader to search the mod for.
    :return: The list of files for the mod.
    """
    versions = call_endpoint(f"/v2/project/{mod_id}/version", options={
        "loaders": f"[\"{mod_loader}\"]",
        "game_versions": f"[\"{version}\"]"
    })
    return [version["files"] for version in versions]
