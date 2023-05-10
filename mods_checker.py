"""This script checks for updates of your mods for the current Minecraft version."""
import contextlib
import os
import re
import shutil
import subprocess
import sys

import psutil
import requests
from beaupy import select, select_multiple, confirm
from halo import Halo
from send2trash import send2trash

from curseforge_api import get_minecraft_versions
from utils import Color, ModLoader, SearchMethod, SearchWebsite

VERSION = "1.1.0"


def diff_between_files(file1: str, file2: str) -> dict:
    """Return the difference between two file names."""
    diffs = {}
    file1 = re.sub("[+ _]", "-", file1.removesuffix(".jar"))
    file2 = re.sub("[+ _]", "-", file2.removesuffix(".jar"))
    for s1, s2 in zip(file1.split("-"), file2.split("-")):
        if s1 != s2:
            # Compare the parsed strings to int
            try:
                s1_num = int(s1.replace(".", ""))
                s2_num = int(s2.replace(".", ""))
                if s2_num > s1_num:
                    diffs[s1] = s2
            except ValueError:
                diffs[s1] = s2
    return diffs


def check_for_updates(map_of_mods: dict[str, dict], mc_version: str, mod_loader: ModLoader):
    """
    Check for updates of the mods.
    :param map_of_mods: The map of mods. The key is the local file name, the value is the CurseForge mod.
    :param mc_version: The Minecraft version to search the mod for.
    :param mod_loader: The mod loader to search the mod for.
    :return: A tuple containing the updates, the messages and the errors.
    """
    _updates: dict[str, dict] = {}
    _updates_messages: [str] = []
    _updates_errors: [str] = []
    # Loop through the mods map
    for local_file, mod in map_of_mods.items():
        # Get the origin website to adapt the algorithm
        if "latestFiles" in mod:
            website = SearchWebsite.CURSEFORGE
            valid = [file for file in mod["latestFiles"] if file["isAvailable"] and mc_version in file["gameVersions"]]
            files = sorted(valid, key=lambda file: file["fileDate"], reverse=True)
        else:
            website = SearchWebsite.MODRINTH
            files = mod["files"]
        # Handle errors
        if not files:
            _updates_errors.append(f"{mod['name'] if website == SearchWebsite.CURSEFORGE else mod['title']}: "
                                   + f"No file found for {mc_version}, please check and download manually "
                                   + (
                                       f"at {mod['links']['websiteUrl']}" if website == SearchWebsite.CURSEFORGE
                                       else "on Modrinth"
                                   ))
            continue
        # Check for updates
        for file in files:
            if website == SearchWebsite.CURSEFORGE:
                file_mod_loaders = [mod_loader for mod_loader in ModLoader if str(mod_loader) in file["fileName"].lower()]
                # Continue only if the mod loader is the same or if the file doesn't have a mod loader
                if file_mod_loaders:
                    file_mod_loader = file_mod_loaders[0]
                    if file_mod_loader != mod_loader:
                        continue
            filename = file["fileName"] if website == SearchWebsite.CURSEFORGE else file["filename"]
            if filename == local_file:
                break
            # Check if the file is different
            if diff_between_files(local_file, filename):
                _updates[local_file] = {
                    "fileName": filename,
                    "downloadUrl": file["downloadUrl"] if website == SearchWebsite.CURSEFORGE else file["url"],
                }
                _updates_messages.append(f"{mod['name'] if website == SearchWebsite.CURSEFORGE else mod['title']}: "
                                         + f"{Color.YELLOW}{local_file}{Color.RESET} -> "
                                         + f"{Color.GREEN}{filename}{Color.RESET}")
                break
    return _updates, _updates_messages, _updates_errors


def download_file(url: str, fallback_name: str) -> tuple[bool, str | None]:
    """
    Download a file from a URL.
    :param url: The URL to download the file from.
    :param fallback_name: The fallback name to use if the file name can't be determined.
    :return: True if the file was downloaded successfully, False otherwise.
    """
    try:
        with requests.get(url) as dl_response:
            file_name = fallback_name
            if "Content-Disposition" in dl_response.headers.keys():
                file_name = re.findall("filename=(.+)", dl_response.headers["Content-Disposition"])[0]
            else:
                url_name = url.split("/")[-1]
                if url_name:
                    file_name = url_name

            with open(file_name, "xb") as file:
                file.write(dl_response.content)
            return True, file_name
    except requests.exceptions.RequestException:
        return False, None


def leave(error: bool = False, message: str = None, silent: bool = False):
    """Exit the script."""
    if error:
        if not silent:
            print(f"{Color.RED}{'An error occurred! Exiting.' if not message else message}{Color.RESET}",
                  file=sys.stderr)
        sys.exit(1)
    else:
        if not silent:
            print(f"{Color.GREEN}{'Goodbye!' if not message else message}{Color.RESET}")
        sys.exit(0)


if __name__ == "__main__":
    # Check if the CURSEFORGE_API_KEY exists in .env
    if os.path.exists(".env"):
        env_key_found = False
        for line in open(".env"):
            if line.startswith("CURSEFORGE_API_KEY"):
                env_key_found = True
                if not line.split("=")[1].strip():
                    leave(True, "Please provide a value for CURSEFORGE_API_KEY in .env")
                break
        if not env_key_found:
            leave(True, "Please set the CURSEFORGE_API_KEY in .env")
    else:
        leave(True, "Please create a .env file and set the CURSEFORGE_API_KEY")

    # Start the script
    with contextlib.chdir(f"{os.getenv('APPDATA')}/.minecraft/mods"):
        mods = [mod for mod in os.listdir() if os.path.isfile(mod)]
        if not mods:
            leave(True, "No mods found in the mods folder")
        mc_versions = get_minecraft_versions()
        mc_versions.reverse()  # Sort from latest to oldest

        # Determine the current version and mod loader
        version_matches: dict[str, int] = {}
        mod_loader_matches: dict[ModLoader, int] = {}
        spinner = Halo(text="Determining Minecraft version and mod loader")
        spinner.start()
        for mod in mods:
            mod_mod_loaders = [mod_loader for mod_loader in ModLoader if str(mod_loader) in mod.lower()]
            if mod_mod_loaders:
                mod_mod_loader = mod_mod_loaders[0]
                mod_loader_matches[mod_mod_loader] = mod_loader_matches.get(mod_mod_loader, 0) + 1
            for version in mc_versions:
                if version in mod:
                    version_matches[version] = version_matches.get(version, 0) + 1
                    break
        current_mc_version = max(version_matches, key=version_matches.get)
        current_mod_loader = max(mod_loader_matches, key=mod_loader_matches.get)
        spinner.succeed(f"{Color.CYAN}mc-mods-checker v{VERSION}{Color.RESET} - "
                        f"Minecraft {Color.GREEN}{current_mc_version}{Color.RESET} "
                        f"({Color.MAGENTA}{current_mod_loader.name()}{Color.RESET} Mod Loader)")

        # Map the mods to their CurseForge/Modrinth mod
        mods_map: dict[str, dict] = {}
        not_found_mods = []
        spinner = Halo(
            text=f"Finding installed mod{'s' if len(mods) > 1 else ''} on CurseForge and Modrinth (0/{len(mods)})"
        )
        spinner.start()
        for index, mod in enumerate(mods):
            # Update the spinner
            spinner.text = f"Finding installed mod{'s' if len(mods) > 1 else ''} on CurseForge and Modrinth ({index + 1}/{len(mods)})"

            # Build the query from the mod name
            split_mod = mod.replace("_", "-").split("-")
            first_numbered_word = next(element for element in split_mod if any(char.isdigit() for char in element))
            first_words_before_number = split_mod[:split_mod.index(first_numbered_word)]
            query_without_loader = first_words_before_number[:-1] \
                if first_words_before_number[-1] in ["fabric", "forge"] \
                else first_words_before_number
            search_query = " ".join(query_without_loader)

            # Search for the mod in CurseForge
            for search_method in SearchMethod:
                result = search_method.search(
                    search_query,
                    current_mc_version,
                    current_mod_loader
                )
                if result:
                    mods_map[mod] = result
                    break

            # If the mod was not found, add it to the list of not found mods
            if not result:
                not_found_mods.append(mod)
        # Update the spinner according to the results
        if not_found_mods:
            if len(not_found_mods) == len(mods):
                spinner.fail("No mods were found on CurseForge nor Modrinth" if len(mods) > 1 else
                             "Your mod was not found on CurseForge nor Modrinth")
            elif len(not_found_mods) == 1:
                if len(mods) > 1:
                    spinner.warn(f"{Color.YELLOW}1 mod was not found on CurseForge nor Modrinth: "
                                 f"{not_found_mods[0]}{Color.RESET}")
                else:
                    spinner.warn(f"{Color.YELLOW}Your mod was not found on CurseForge nor Modrinth{Color.RESET}")
            else:
                spinner.warn(f"{Color.YELLOW}{len(not_found_mods)} mods were not found on CurseForge nor Modrinth: "
                             f"{', '.join(not_found_mods)}{Color.RESET}")
        else:
            spinner.succeed("All mods were found on CurseForge and Modrinth" if len(mods) > 1 else
                            "Your mod was found on CurseForge and Modrinth")

        # Act depending on whether the current version is the latest or not
        if current_mc_version == mc_versions[0]:  # Current version is the latest
            spinner = Halo(text="Checking for mod updates for the current Minecraft version")
            spinner.start()
            # Check for updates of current mods
            updates, updates_messages, updates_errors = check_for_updates(mods_map, current_mc_version,
                                                                          current_mod_loader)
            if not updates:
                spinner.succeed(
                    f"No update{'s were' if len(updates) > 1 else ' was'} found for your mod{'s' if len(mods) > 1 else ''}"
                )
                leave(False)
            spinner.info(('Updates are' if len(updates) > 1 else 'An update is')
                         + f" available for {len(updates)} of your {len(mods)} mod{'s' if len(mods) > 1 else ''}:\n\t"
                         + "\n\t".join(updates_messages) + (
                             f"\n  {Color.RED}The following errors occurred:\n\t"
                             + "\n\t".join(updates_errors) + str(Color.RESET) if updates_errors else ""
                         ))

            # Ask the user whether to update the mods
            print(f"{Color.BLUE}>{Color.RESET} What do you want to do?")
            if len(mods) > 1:
                if len(updates) > 1:  # Multiple mods to update
                    match select(["Apply all updates", "Update only some mods", "Don't update any mod"],
                                 return_index=True):
                        case 1:
                            # Ask the user which mods to update
                            print(f"{Color.BLUE}>{Color.RESET} Select the mods to update:")
                            selected_updates = select_multiple(
                                [f"{old} -> {new['fileName']}" for old, new in updates.items()],
                                return_indices=True
                            )
                            if not selected_updates:
                                leave(True, "Please select at least one mod to update")
                            updates = {
                                old: new for index, (old, new) in enumerate(updates.items()) if
                                index in selected_updates
                            }
                        case 2:
                            leave(False)
                elif not confirm("Do you want to apply the update?"):  # Multiple mods but only one to update
                    leave(False)
            elif not confirm("Do you want to update your mod?"):  # Only one mod
                leave(False)

            # Update the mods and send the old ones to the trash
            spinner = Halo(text=f"Updating your mod{'s' if len(updates) > 1 else ''} (0/{len(updates)})")
            spinner.start()
            update_failures = 0
            for index, (current_file, update_file) in enumerate(updates.items()):
                download_success, _ = download_file(update_file["downloadUrl"], update_file["fileName"])
                spinner_msg = f"Updating your mod{'s' if len(updates) > 1 else ''} ({index + 1}/{len(updates)}) " \
                              f"- Done: {update_file['fileName']}"
                if download_success:
                    send2trash(current_file)
                else:
                    update_failures += 1
                if update_failures:
                    spinner_msg += f" {Color.RED}({update_failures} failed){Color.RESET}"
                spinner.text = spinner_msg
            if update_failures:
                if update_failures == len(updates):
                    spinner.fail(f"Failed to update {update_failures} mod{'s' if update_failures > 1 else ''}")
                else:
                    spinner.warn(
                        f"Updated {len(updates) - update_failures} mod{'s' if len(updates) - update_failures > 1 else ''}," +
                        f"{update_failures} failed"
                    )
            else:
                spinner.succeed(f"Updated {len(updates)} mod{'s' if len(updates) > 1 else ''}")

        else:  # Current version is not the latest
            spinner = Halo(
                text=f"Minecraft {mc_versions[0]} is available, checking for mod upgrade{'s' if len(mods) > 1 else ''} for it"
            )
            spinner.start()
            # Check for updates of current mods
            new_versions, new_versions_messages, new_versions_errors = check_for_updates(mods_map, mc_versions[0],
                                                                                         current_mod_loader)
            if not new_versions:
                spinner.fail(("None of your mods are" if len(mods) > 1 else "You mod isn't")
                             + f" yet available for the latest Minecraft version ({mc_versions[0]})")
                leave(True, silent=True)
            if len(new_versions) == len(mods):
                if len(mods) > 1:
                    updates_summary = "All your mods are"
                else:
                    updates_summary = "Your mod is"
            else:
                updates_summary = f"{len(new_versions)} of your {len(mods)} mods are"
            spinner.info(updates_summary + f" available for Minecraft {mc_versions[0]}:\n\t"
                         + "\n\t".join(new_versions_messages) + (
                             f"\n  {Color.RED}The following errors occurred:\n\t"
                             + "\n\t".join(new_versions_errors) + str(Color.RESET) if new_versions_errors else ""
                         ))

            # Ask the user whether to update the mods
            if not confirm(f"Do you want to upgrade {len(new_versions)} mod{'s' if len(new_versions) > 1 else ''}?"):
                sys.exit(0)

            # Move the mods to a sub folder or trash
            stores_previous_versions = [folder for folder in os.listdir()
                                        if os.path.isdir(folder) and folder in mc_versions]
            if stores_previous_versions:
                spinner = Halo(text=f"Moving your mod{'s' if len(mods) > 1 else ''} to their sub folder")
                spinner.start()
                os.mkdir(current_mc_version)
                for mod in mods:
                    shutil.move(mod, current_mc_version)
                spinner.succeed(
                    f"Moved {len(mods)} mod{'s' if len(mods) > 1 else ''} to the {current_mc_version} sub folder"
                )
            else:
                spinner = Halo(text=f"Moving your mod{'s' if len(mods) > 1 else ''} to trash")
                spinner.start()
                for mod in mods:
                    send2trash(mod)
                spinner.succeed(f"Moved {len(mods)} mod{'s' if len(mods) > 1 else ''} to trash")

            # If Fabric, download fabric.exe and run it
            if current_mod_loader == ModLoader.FABRIC:
                spinner = Halo(text="Fabric detected, downloading Fabric Installer")
                spinner.start()
                # Fetch the latest version of Fabric Installer
                for server in ["https://meta.fabricmc.net", "https://meta2.fabricmc.net"]:
                    try:
                        response = requests.get(f"{server}/v2/versions/installer")
                        response.raise_for_status()
                        installer_versions = response.json()
                        # Set fabric_installer_url to the url of the first stable version
                        for version in installer_versions:
                            if version["stable"]:  # Stable version should always be the first/latest one
                                fabric_installer_url = version["url"]
                        break
                    except requests.exceptions.RequestException:
                        continue
                if not fabric_installer_url:
                    spinner.fail("Failed to fetch the latest version of Fabric Installer")
                    leave(True, silent=True)

                # Download Fabric Installer
                download_success, fabric_installer = download_file(fabric_installer_url, "fabric-installer.jar")
                if not download_success:
                    spinner.fail("Failed to download Fabric Installer")
                    leave(True, silent=True)

                # Close the Minecraft launcher if it is running
                # kill any running Minecraft processes
                for process in psutil.process_iter():
                    if "minecraft" in process.name().lower():
                        process.kill()

                # Run Fabric Installer
                spinner = Halo(text="Running Fabric Installer, please proceed with the installation and then close it")
                spinner.start()
                try:
                    subprocess.run(["java", "-jar", fabric_installer])  # Assuming Java is installed and in PATH
                except subprocess.CalledProcessError:
                    spinner.fail("Failed to run Fabric Installer")
                    leave(True, silent=True)
                send2trash(fabric_installer)
                spinner.succeed("Fabric Installer ran successfully")

            # Download mods for the latest version
            spinner = Halo(
                text=f"Downloading {len(new_versions)} mod{'s' if len(new_versions) > 1 else ''} for Minecraft {mc_versions[0]}"
            )
            spinner.start()
            download_failures = 0
            for index, (current_file, update_file) in enumerate(new_versions.items()):
                download_success, _ = download_file(update_file["downloadUrl"], update_file["fileName"])
                spinner_msg = f"Downloading {len(new_versions)} mod{'s' if len(new_versions) > 1 else ''} for Minecraft {mc_versions[0]} ({index + 1}/" \
                              + f"{len(new_versions)})"
                if not download_success:
                    download_failures += 1
                if download_failures:
                    spinner_msg += f" {Color.RED}({download_failures} failed){Color.RESET}"
                spinner.text = spinner_msg
            if download_failures:
                if download_failures == len(new_versions):
                    spinner.fail(f"Failed to download {download_failures} mod{'s' if download_failures > 1 else ''}")
                else:
                    spinner.warn(
                        f"Downloaded {len(new_versions) - download_failures} mod{'s' if len(new_versions) - download_failures > 1 else ''}, {download_failures} failed"
                    )
            else:
                spinner.succeed(f"Downloaded {len(new_versions)} mod{'s' if len(new_versions) > 1 else ''}")
