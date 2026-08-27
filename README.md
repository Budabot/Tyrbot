# Tyrbot

Tyrbot is an in-game chatbot for the MMORPG Anarchy Online released by Funcom in 2001.

This is a rewrite of [Budabot](https://github.com/Budabot/Budabot) in Python 3.

Note: this project is now in maintenance mode and will not receive any more major updates, fixes, or new features.

## Quickstart

1. Download the bot: https://github.com/Budabot/Tyrbot/archive/master.zip
1. Unzip the bot to a location on your computer
1. Run `start.bat` (Windows) or `./start.sh` (Linux/macOS)
1. The first time you run the bot it will ask some questions. You will need four pieces of information: username, password, character name, and superadmin. For any other question you can simply press &lt;Enter&gt; to use the default value.

> [!NOTE]
> The startup scripts automatically manage Python environment setup and dependency installation using `uv`. No manual virtual environment creation or package installation is required.

## Requirements

- Python 3.12 (managed automatically via `uv` by startup scripts, or provided by your system)
- Supported platforms: Windows, Linux, macOS

## Environment & Dependency Management (`uv`)

Tyrbot uses [uv](https://github.com/astral-sh/uv) and `uv venv` for fast, reproducible virtual environment provisioning and package management, replacing legacy `virtualenv` and standard `pip`.

### Automated Setup via Startup Scripts

- **Windows (`start.bat`)**:
  - Automatically downloads `uv.exe` with SHA256 checksum verification (via `win32/download_uv.bat` referencing `UV_VERSION`).
  - Checks for a valid `venv/pyvenv.cfg`; if missing or created with a legacy environment tool, it automatically cleans up and initializes a fresh `uv venv venv --python 3.12`.
  - Installs and updates project dependencies using `%UV% pip install --python venv\Scripts\python.exe -r requirements.txt`.
  - Launches the bot via `venv\Scripts\python.exe bootstrap.py`.

- **Linux / macOS (`start.sh`)**:
  - Automatically downloads the platform-specific `uv` binary (Linux/macOS x86_64 or arm64/aarch64) with SHA256 checksum verification.
  - Automatically detects missing or legacy virtual environments and initializes `uv venv venv --python 3.12`.
  - Installs and updates dependencies using `./uv pip install --python venv/bin/python -r requirements.txt`.
  - Launches the bot via `venv/bin/python bootstrap.py`.

### Developer & Manual Setup

If you prefer to manage the environment manually using `uv`:

1. **Install `uv`** (if not already installed):
   - See [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) or use the provided scripts.
2. **Create virtual environment**:
   ```bash
   uv venv venv --python 3.12
   ```
3. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```
4. **Run the bot**:
   ```bash
   uv run bootstrap.py
   # or activate the virtual environment:
   # Linux/macOS: source venv/bin/activate && python bootstrap.py
   # Windows:     venv\Scripts\activate && python bootstrap.py
   ```

### Troubleshooting & Self-Healing

- **Missing `pyvenv.cfg` or broken virtualenv**:
  If the virtual environment becomes corrupted or is missing `pyvenv.cfg`, simply run `start.bat` (Windows) or `./start.sh` (Linux/macOS). The scripts will detect the missing configuration, remove the invalid directory, and recreate a clean `uv venv` environment automatically.
- **Upgrading from legacy `virtualenv`**:
  Existing installations running older virtualenv-based environments are automatically detected and cleanly migrated to `uv venv` upon executing `start.bat` or `start.sh`.

## Installation

Currently there are no releases for Tyrbot but you can download the bot from here which will always have the very latest changes: https://github.com/Budabot/Tyrbot/archive/master.zip

Then simply unzip the bot somewhere before starting it.

## Upgrade

If you are already running Tyrbot and simply want to upgrade to the latest version, follow these steps:

1. Download the latest version from here: https://github.com/Budabot/Tyrbot/archive/master.zip
1. Unzip the bot to a new location (do not just unzip it over the top of the old installation)
1. From the old installation, copy the `./conf`, `./data`, and optionally, the `./logs` directories to the new installation
1. If you have any custom modules, copy the `./modules/custom/` directory over as well
1. Start the bot (`start.bat` or `./start.sh`) and verify that everything works and that all of your data has carried over. The startup script will automatically initialize the `uv` environment and install all dependencies.
1. In a few rare cases, the bot may not start because the config file format changed between versions and you may need to compare your `conf/config.py` file to the template version (`conf/config_template.py`) and make changes accordingly
1. You can now delete the old installation

## Starting Tyrbot

To start the bot, run either `start.bat` (Windows) or `start.sh` (Linux/macOS).

If it is your first time running the bot, or if the config.py file does not exist, it will take you through the configuration wizard to configure the bot. You will need to have a character that the bot will run as along with the username and password for the account that has that character. If you want to run this bot as an org bot, that character will need to already be a member of that org.

## Running in Docker

Tyrbot Docker images (`Dockerfile` and `Dockerfile.test`) use the official combined Astral image (`FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim`) as our base image. Containerized dependency installation is then handled using `uv pip install` for fast, reliable, and reproducible builds.

For detailed Docker setup instructions, see the Wiki page: https://github.com/Budabot/Tyrbot/wiki/Docker-Setup

## Support

If you need help or support with Tyrbot, join our discord channel: https://discord.gg/2x9WesJ

## Discord Module Setup

If you would like to connect your bot to your Discord server, follow this guide: https://github.com/Budabot/Tyrbot/wiki/Discord-Setup

- The library used to build the module can be found https://discordpy.readthedocs.io/en/latest/index.html.
- The official Discord API documentation can be found https://discordapp.com/developers/docs/intro.
- The official Discord API server can be joined at https://discord.gg/discord-api.

## Writing Custom Modules

See the Wiki page: https://github.com/Budabot/Tyrbot/wiki/Writing-Custom-Modules
