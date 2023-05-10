"""Utility functions and classes."""
from enum import Enum

import enchant

from curseforge_api import search_mod
from modrinth_api import search_mod as search_mod_modrinth, get_files_for_mod


class ModLoader(Enum):
    """Enum for the different mod loaders."""
    FORGE = 1
    CAULDRON = 2
    LITELOADER = 3
    FABRIC = 4
    QUILT = 5

    def __str__(self):
        return self.name().lower()

    def name(self):
        """
        Get the name of the mod loader.
        :return: The name of the mod loader.
        """
        match self:
            case ModLoader.FORGE:
                return "Forge"
            case ModLoader.CAULDRON:
                return "Cauldron"
            case ModLoader.LITELOADER:
                return "LiteLoader"
            case ModLoader.FABRIC:
                return "Fabric"
            case ModLoader.QUILT:
                return "Quilt"


class Color(Enum):
    """Enum for the different colors."""
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    def __add__(self, other):
        return self.value + (other.value if isinstance(other, Color) else other)

    def __str__(self):
        return self.value


class SearchWebsite(Enum):
    """Enum for the different search websites."""
    MODRINTH = "Modrinth"
    CURSEFORGE = "Curseforge"


class SearchMethod(Enum):
    """Enum for the different search methods."""
    MODRINTH_QUERY = "Modrinth (query)"
    CURSEFORGE_SLUG = "Curseforge (slug)"
    CURSEFORGE_QUERY = "Curseforge (query)"
    CURSEFORGE_SPACED_SLUG = "Curseforge (slug with spaces)"
    CURSEFORGE_SPACED_QUERY = "Curseforge (query with spaces)"

    @staticmethod
    def __add_spaces_from_uppercase(text: str):
        """
        Add spaces before uppercase letters if the previous letter is not an uppercase letter.
        More subtle checks are performed to add spaces as smartly as possible.
        """
        new_text = ""
        new_word = ""
        for i, char in enumerate(text):
            if i > 0:
                last_char = text[i - 1]
                if char.isupper() and not last_char.isupper() and not text[i - len(new_word):i].islower():
                    # Add a space before an uppercase letter if the previous letter is not an uppercase
                    new_text += " "
            new_text += char
            if char == " ":
                # Save the beginning of a new word
                new_word = ""
            else:
                new_word += char
        return new_text

    @staticmethod
    def __add_spaces_from_dictionary(text: str):
        """Add spaces between words based on the english dictionary."""
        d = enchant.Dict("en_US")
        new_text = ""
        worked_on_word = text
        while worked_on_word:
            for i in range(len(worked_on_word), 0, -1):
                word = worked_on_word[:i]
                if d.check(word):
                    new_text += word
                    if i != len(worked_on_word):
                        new_text += " "
                    worked_on_word = worked_on_word[i:]
                    break
        return new_text

    @staticmethod
    def __find_closest_match(results: list[dict], mod_name: str) -> dict | None:
        """
        Find the closest match in the results based on the mod name.
        To do so, the first words of each result are compared to the mod name.
        """
        if not results:
            return None
        if len(results) == 1:
            return results[0]
        for result in results:
            result_first_words = " ".join(result["name"].split(" ")[:mod_name.count(" ") + 1]).lower()
            if result_first_words == mod_name.lower():
                return result

    def search(self, name: str, version: str, mod_loader: ModLoader) -> dict | None:
        """Return the mod that matches the name and version using the search method."""
        query = self.__add_spaces_from_uppercase(name) \
            if self == SearchMethod.CURSEFORGE_SLUG or self == SearchMethod.CURSEFORGE_QUERY \
            else self.__add_spaces_from_dictionary(name)
        match self:
            case SearchMethod.MODRINTH_QUERY:
                search = search_mod_modrinth(
                    version=version,
                    mod_loader=mod_loader.name().lower(),
                    query=name
                )
                if search:
                    first_result = search[0]
                    files = get_files_for_mod(first_result["slug"], version, mod_loader.name().lower())
                    return {**first_result, "files": [file for sublist in files for file in sublist]}
            case SearchMethod.CURSEFORGE_SLUG:
                search = search_mod(
                    version=version,
                    mod_loader=mod_loader.value,
                    slug=query.lower().replace(" ", "-")
                )
                if search:
                    return search[0]
            case SearchMethod.CURSEFORGE_QUERY:
                search = search_mod(
                    version=version,
                    mod_loader=mod_loader.value,
                    query=query
                )
                if search:
                    return self.__find_closest_match(search, name)
            case SearchMethod.CURSEFORGE_SPACED_SLUG:
                search = search_mod(
                    version=version,
                    mod_loader=mod_loader.value,
                    slug=query.lower().replace(" ", "-")
                )
                if search:
                    return search[0]
            case SearchMethod.CURSEFORGE_SPACED_QUERY:
                search = search_mod(
                    version=version,
                    mod_loader=mod_loader.value,
                    query=query
                )
                if search:
                    return self.__find_closest_match(search, query)

    def color(self):
        """Return the color associated with the search method. Used for debugging."""
        match self:
            case SearchMethod.MODRINTH_QUERY:
                return Color.RED
            case SearchMethod.CURSEFORGE_SLUG:
                return Color.BLUE
            case SearchMethod.CURSEFORGE_QUERY:
                return Color.GREEN
            case SearchMethod.CURSEFORGE_SPACED_SLUG:
                return Color.MAGENTA
            case SearchMethod.CURSEFORGE_SPACED_QUERY:
                return Color.CYAN
