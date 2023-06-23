# mc-mods-checker

Updates your local Minecraft mods.

![Demo](demo/demo.gif)
:---:
*Demo of v1.0.1*

## Features

- Scan your mods folder and find the matching CurseForge page for each mod
- Check for mod updates for your current Minecraft version
- Update your mods to the latest Minecraft version if any is available
- Move your old mods to a backup folder (switching to a newer Minecraft version) or send them to the trash

## Configuration

You will need a CurseForge API key to use this script with CurseForge.
You can get one [here](https://console.curseforge.com/#/api-keys).
Simply create an account, give your organization a name and copy the key alongside the script in a file named `.env`.

```
# mc-mods-checker/.env
CURSEFORGE_API_KEY=your_key_here
```

If you don't provide an API key, the script will only work with Modrinth.

## Usage

This script requires Python 3.11+.

```shell
$ git clone https://github.com/WarningImHack3r/mc-mods-checker
$ cd mc-mods-checker
$ pip install -r requirements.txt
$ python3 mods_checker.py
```

## TODO
- [ ] Change mod online detection mechanism to use current mod version instead of target version
- [ ] Only work with Modrinth if no API key is provided
- [ ] Auto install Fabric option (with `.jar` version & `java -jar fabric-installer.jar client -dir "/path/to/.minecraft"`)
- [ ] Add auto-update feature
