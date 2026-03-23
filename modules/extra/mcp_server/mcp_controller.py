import asyncio
import re
import threading
from html.parser import HTMLParser

import uvicorn
from mcp.server.fastmcp import FastMCP

from core.chat_blob import ChatBlob
from core.decorators import instance, event
from core.logger import Logger
from core.setting_types import NumberSettingType, TextSettingType, BooleanSettingType


def _strip_ao_markup(text: str) -> str:
    """Strip AO/HTML markup tags and return clean plain text."""
    # Expand AO pseudo-tags before stripping
    text = re.sub(r"<symbol>", "!", text)
    text = re.sub(r"<tab>", "    ", text)
    text = re.sub(r"<br>", "\n", text)

    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self._parts: list[str] = []
            self._popup_content: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                for name, value in attrs:
                    if name == "href" and value.startswith("text://"):
                        self._popup_content.append(value[7:])

        def handle_data(self, data):
            self._parts.append(data)
            
        def error(self, msg):
            pass
            
        def result(self):
            out = "".join(self._parts)
            if self._popup_content:
                out += "\n\n--- Detailed Info ---\n"
                out += "\n".join(self._popup_content)
            return out

    s = _Stripper()
    s.feed(text)
    return s.result()


def _response_to_text(response) -> str:
    """Convert a Tyrbot command response (str or ChatBlob) to clean plain text."""
    if isinstance(response, ChatBlob):
        body = _strip_ao_markup(response.msg or "")
        return f"[{response.title}]\n{body}".strip()
    return _strip_ao_markup(str(response))


@instance()
class McpController:
    def __init__(self):
        self.logger = Logger(__name__)
        self._server_thread: threading.Thread | None = None
        self._uvicorn_server: uvicorn.Server | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mcp: FastMCP | None = None

    def inject(self, registry):
        self.setting_service = registry.get_instance("setting_service")
        self.command_service = registry.get_instance("command_service")
        self.character_service = registry.get_instance("character_service")
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")

    def start(self):
        self.setting_service.register(
            self.module_name,
            "mcp_server_enabled",
            False,
            BooleanSettingType(),
            "Enable or disable the MCP HTTP server (this enables superadmin access to your bot, do not enable unless you understand the risks)",
        )
        self.setting_service.register_change_listener("mcp_server_enabled", self.mcp_server_enabled_changed)

        self.setting_service.register(
            self.module_name,
            "mcp_server_host",
            "127.0.0.1",
            TextSettingType(options=["127.0.0.1"]),
            "The host address the MCP HTTP server listens on",
        )
        self.setting_service.register(
            self.module_name,
            "mcp_server_port",
            8765,
            NumberSettingType(),
            "The port the MCP HTTP server listens on",
        )

    def _build_mcp(self, host: str, port: int) -> FastMCP:
        """Create and configure the FastMCP instance with its tools."""
        mcp = FastMCP(
            name="TyrbotMCP",
            host=host,
            port=port,
            # Disable DNS-rebinding protection so external callers can connect.
            # Remove / adjust if you only need localhost access.
            transport_security=None,
        )

        # Capture services in closure so the tool function is self-contained
        _cs = self.command_service
        _char_service = self.character_service
        _bot = self.bot
        _logger = self.logger
        _text = self.text

        @mcp.resource("tyrbot://commands")
        def list_commands() -> str:
            """Return a JSON list of all registered Tyrbot commands grouped by module.

            Each entry contains:
              - command: the command name
              - sub_command: sub-command qualifier (empty string if none)
              - module: the module that registered the command
              - access_level: minimum access level required
              - channels: list of channels the command is available in
              - enabled: whether the command is currently enabled
              - description: short description from the command handler
            """
            import json

            # generate command list data
            command_list: list[dict] = []
            for key, handlers in self.command_service.handlers.items():
                for handler in handlers:
                    command, _AddableT1 = _cs.get_command_key_parts(key)

                    command_data = {
                        "command": command,
                        "module": handler["callback"].__self__.__class__.__module__,
                        "params": list(map(lambda x: x.get_name(), handler["params"])),
                        "description": handler["description"],
                    }

                    command_list.append(command_data)

            return json.dumps(command_list, indent=2)

        @mcp.tool()
        def command(query: str) -> str:
            """Execute any Tyrbot command and return its response as plain text.

            Pass the full command string exactly as you would type it in-game,
            without a leading command symbol.  Examples:
              query="about"
              query="config settings list"
              query="whois Tyrbot"
            """
            conn = _bot.get_primary_conn()

            _logger.log_chat(conn, "MCP Server", "Query", query)

            # Resolve superadmin char_id so all commands pass access checks
            try:
                char_id = _char_service.resolve_char_to_id(_bot.superadmin)
            except Exception:
                char_id = None

            results: list[str] = []

            def reply(msg):
                results.append(msg)

            _cs.process_command(
                message=query.strip(),
                channel="msg",
                char_id=char_id,
                reply=reply,
                conn=conn,
            )

            # format log output
            for result in results:
                pages = []
                if isinstance(result, ChatBlob):
                    pages = self.text.paginate(result, conn, max_page_length=None)
                else:
                    pages = [self.text.format_message(result, conn)]
                
                for page in pages:
                    _logger.log_chat(conn, "MCP Server", "Response", page)

            return "\n\n---\n\n".join(map(_response_to_text, results)) if results else "(no response)"

        return mcp

    def start_mcp_server(self):
        """Spin up the Streamable-HTTP MCP server in a background daemon thread."""
        self.stop_mcp_server()
        
        self.logger.info("Starting Streamable-HTTP MCP server")

        host = self.setting_service.get("mcp_server_host").get_value()
        port = int(self.setting_service.get("mcp_server_port").get_value())

        self._mcp = self._build_mcp(host, port)
        starlette_app = self._mcp.streamable_http_app()

        config = uvicorn.Config(
            app=starlette_app,
            host=host,
            port=port,
            log_level="warning",
            # uvicorn needs its own event loop inside the thread
            loop="asyncio",
        )
        self._uvicorn_server = uvicorn.Server(config)

        def run_server():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._uvicorn_server.serve())
            finally:
                self._loop.close()

        self._server_thread = threading.Thread(
            target=run_server,
            name="mcp-http-server",
            daemon=True,
        )
        self._server_thread.start()
        self.logger.info(f"MCP Streamable-HTTP server started on http://{host}:{port}/mcp")

    def stop_mcp_server(self):
        """Gracefully stop the MCP HTTP server (call this on bot shutdown if needed)."""
        self.logger.info(f"Stopping Streamable-HTTP MCP server")
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
        if self._server_thread:
            self._server_thread.join(timeout=5)
            self._server_thread = None
        self.logger.info(f"Streamable-HTTP MCP server has been stopped")

    @event(event_type="connect", description="Log MCP server readiness on bot connect", is_system=True)
    def handle_connect(self, event_type, event_data):
        if self.setting_service.get("mcp_server_enabled").get_value():
            self.start_mcp_server()

    def mcp_server_enabled_changed(self, setting_name, old_value, new_value):
        if new_value == 0:
            self.stop_mcp_server()
        elif new_value == 1:
            self.start_mcp_server()
