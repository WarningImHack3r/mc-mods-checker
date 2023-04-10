"""Curseforge API wrapper"""
import os
from functools import cache

import requests
from dotenv import load_dotenv

load_dotenv()


# Utils
def call_endpoint(endpoint: str, options: dict = None) -> list[dict]:
    """
    Call an endpoint of the Curseforge API.
    :param endpoint: The endpoint to call.
    :param options: The options to pass to the endpoint.
    :return: The data returned by the endpoint.
    """
    r = requests.get(f"https://api.curseforge.com{endpoint}", params=options, headers={
        "Accept": "application/json",
        "x-api-key": os.getenv("CURSEFORGE_API_KEY")
    })
    return r.json()["data"]


# Functions
@cache
def get_minecraft_versions():
    """
    Get the list of Minecraft versions.
    :return: The list of Minecraft versions.
    """
    versions = call_endpoint("/v1/minecraft/version", options={
        "sortDescending": True
    })
    versions_string = list(map(lambda version: version["versionString"], versions))
    versions_string.reverse()
    return versions_string


@cache
def search_mod(version: str, mod_loader: int, slug: str = None, query: str = None):
    """
    Search for a mod on Curseforge.
    :param version: The Minecraft version to search the mod for.
    :param mod_loader: The mod loader to search the mod for.
    :param slug: <Optional> The slug of the mod.
    :param query: <Optional> The query to search the mod.
    :return: The list of mods resulting from the search.
    """
    if not slug and not query:
        raise ValueError("Either slug or query must be provided")
    return call_endpoint("/v1/mods/search", options={k: v for k, v in {
        "gameId": 432,
        "gameVersion": version,
        "modLoaderType": mod_loader,
        "searchFilter": query,
        "slug": slug
    }.items() if v is not None})
