import asyncio
from typing import Optional, List, Dict, Any
from . import __VERSION__
from .gateway.discord_websocket import DiscordWebSocket, DiscordWebSocketOptions
from .rpc.hieuxyz_rpc import HieuxyzRPC
from .rpc.image_service import ImageService
from .utils.logger import logger
from .gateway.entities.identify import ClientProperties
from .gateway.entities.types import UserFlags


class ClientOptions:
    """Option to initialize Client."""

    def __init__(
        self,
        token: str,
        api_base_url: Optional[str] = None,
        always_reconnect: bool = False,
        properties: Optional[ClientProperties] = None,
        connection_timeout: int = 30000,
    ):
        self.token = token
        self.api_base_url = api_base_url
        self.always_reconnect = always_reconnect
        self.properties = properties
        self.connection_timeout = connection_timeout


class Client:
    """
    The main Client class for interacting with Discord Rich Presence.
    """

    def __init__(self, options: ClientOptions):
        if not options.token:
            raise ValueError("Tokens are required to connect to Discord.")
        self.token = options.token
        self.image_service = ImageService(options.api_base_url)
        self.websocket = DiscordWebSocket(
            self.token,
            DiscordWebSocketOptions(
                always_reconnect=options.always_reconnect,
                properties=options.properties,
                connection_timeout=options.connection_timeout,
            ),
        )
        self.rpcs: List[HieuxyzRPC] = []
        self.user: Optional[Dict] = None
        self.rpc = self.create_rpc()
        self._print_about()
        self.formatters = {
            "email": lambda val, _: "\x1b[90m<Hidden>\x1b[0m" if val else "null",
            "phone": lambda val, _: "\x1b[90m<Hidden>\x1b[0m" if val else "null",
            "avatar": self._format_avatar,
            "banner": self._format_banner,
            "asset": lambda val, _: (
                f'"{val}" (\x1b[34mhttps://cdn.discordapp.com/avatar-decoration-presets/{val}.png\x1b[0m)'
            ),
            "accent_color": lambda val, _: (
                f"{val} (\x1b[33m#{hex(val)[2:].zfill(6).upper()}\x1b[0m)"
                if val
                else "null"
            ),
            "banner_color": lambda val, _: f"\x1b[33m{val}\x1b[0m" if val else "null",
            "expires_at": lambda val, _: f"{val} ({val})" if val else "Never",
            "premium_type": self._format_premium_type,
            "flags": lambda val, _: self._format_flags(val),
            "public_flags": lambda val, _: self._format_flags(val),
            "purchased_flags": lambda val, _: f"\x1b[33m{val}\x1b[0m",
        }

    def create_rpc(self) -> HieuxyzRPC:
        """Create a new RPC instance."""

        async def _on_update():
            await self._send_all_activities()

        new_rpc = HieuxyzRPC(self.image_service, _on_update)
        self.rpcs.append(new_rpc)
        return new_rpc

    def remove_rpc(self, rpc_instance: HieuxyzRPC) -> None:
        """Removes an RPC instance and cleans up its resources."""
        if rpc_instance in self.rpcs:
            rpc_instance.destroy()
            self.rpcs.remove(rpc_instance)
            loop = asyncio.get_running_loop()
            loop.create_task(self._send_all_activities())

    async def _send_all_activities(self):
        """Aggregates activities from all RPC instances and sends them to Discord."""
        potential_activities = await asyncio.gather(
            *(rpc.build_activity() for rpc in self.rpcs)
        )
        activities = [a for a in potential_activities if a is not None]

        status = "online"
        for i in range(len(self.rpcs) - 1, -1, -1):
            if self.rpcs[i].current_status:
                status = self.rpcs[i].current_status
                break

        await self.websocket.send_activity(
            {"since": 0, "activities": activities, "status": status, "afk": True}
        )

    def _print_about(self):
        version = __VERSION__
        print(f"""
  _     _                               
 | |__ (_) ___ _   ___  ___   _ ______  
 | '_ \\| |/ _ \\ | | \\ \\/ / | | |_  /  
 | | | | |  __/ |_| |>  <| |_| |/ /   
 |_| |_|_|\\___|\\__,_/_/\\_\\\\__, /___|  
                          |___/       
  @hieuxyz/rpc v{version}
  A powerful Discord Rich Presence library.
  Developed by: hieuxyz
        """)

    async def run(self) -> Dict:
        """Connect to Discord Gateway."""
        await self.websocket.connect()
        logger.info("Waiting for Discord session to be ready...")
        user = await self.websocket.ready_future
        self.user = user
        self._log_user_profile(user)
        logger.info("Client is ready to send Rich Presence updates.")
        return user

    def close(self, force: bool = False):
        """Close the connection to Discord Gateway."""
        for rpc in self.rpcs:
            rpc.destroy()

        asyncio.create_task(self.websocket.close(force))

    def _format_avatar(self, val, parent):
        if not val:
            return "null"
        ext = "gif" if val.startswith("a_") else "png"
        user_id = parent.get("id")
        url = (
            f"https://cdn.discordapp.com/avatars/{user_id}/{val}.{ext}"
            if user_id
            else ""
        )
        return f'"{val}" {f"(\x1b[34m{url}\x1b[0m)" if url else ""}'

    def _format_banner(self, val, parent):
        if not val:
            return "null"
        ext = "gif" if val.startswith("a_") else "png"
        user_id = parent.get("id")
        url = (
            f"https://cdn.discordapp.com/banners/{user_id}/{val}.{ext}"
            if user_id
            else ""
        )
        return f'"{val}" {f"(\x1b[34m{url}\x1b[0m)" if url else ""}'

    def _format_premium_type(self, val, _):
        if val is None:
            return "null"
        map_types = {0: "None", 1: "Classic", 2: "Nitro", 3: "Basic"}
        return f"{val} (\x1b[32m{map_types.get(val, 'Unknown')}\x1b[0m)"

    def _format_flags(self, flags: int) -> str:
        if flags is None:
            return "0"
        flag_names = []
        if flags & UserFlags.STAFF:
            flag_names.append("Staff")
        if flags & UserFlags.PARTNER:
            flag_names.append("Partner")
        if flags & UserFlags.HYPESQUAD:
            flag_names.append("HypeSquad")
        if flags & UserFlags.BUG_HUNTER_LEVEL_1:
            flag_names.append("BugHunter I")
        if flags & UserFlags.HYPESQUAD_ONLINE_HOUSE_1:
            flag_names.append("Bravery")
        if flags & UserFlags.HYPESQUAD_ONLINE_HOUSE_2:
            flag_names.append("Brilliance")
        if flags & UserFlags.HYPESQUAD_ONLINE_HOUSE_3:
            flag_names.append("Balance")
        if flags & UserFlags.PREMIUM_EARLY_SUPPORTER:
            flag_names.append("EarlySupporter")
        if flags & UserFlags.BUG_HUNTER_LEVEL_2:
            flag_names.append("BugHunter II")
        if flags & UserFlags.VERIFIED_DEVELOPER:
            flag_names.append("VerifiedDev")
        if flags & UserFlags.CERTIFIED_MODERATOR:
            flag_names.append("CertifiedMod")
        if flags & UserFlags.ACTIVE_DEVELOPER:
            flag_names.append("ActiveDev")
        return f"{flags} \x1b[36m[{', '.join(flag_names) if flag_names else 'None'}]\x1b[0m"

    def _print_dynamic_tree(self, obj: Any, prefix: str = ""):
        if isinstance(obj, dict):
            entries = list(obj.items())
            for index, (key, value) in enumerate(entries):
                is_last_item = index == len(entries) - 1
                connector = "└── " if is_last_item else "├── "
                child_prefix = prefix + ("    " if is_last_item else "│   ")
                display_value = ""
                is_object_node = False
                if value is None:
                    display_value = "\x1b[90mnull\x1b[0m"
                elif isinstance(value, dict) and value:  # Not empty dict
                    is_object_node = True
                    print(f"{prefix}{connector}\x1b[1m{key}\x1b[0m")
                    self._print_dynamic_tree(value, child_prefix)
                elif isinstance(value, list):
                    if len(value) > 0 and not isinstance(value[0], (dict, list)):
                        display_value = f"[ {', '.join(map(str, value))} ]"
                    else:
                        display_value = f"[Array({len(value)})]"
                else:
                    if key in self.formatters:
                        try:
                            display_value = self.formatters[key](value, obj)
                        except:
                            display_value = str(value)
                    else:
                        if isinstance(value, str):
                            display_value = f'"\x1b[32m{value}\x1b[0m"'
                        elif isinstance(value, bool):
                            display_value = (
                                "\x1b[32mtrue\x1b[0m"
                                if value
                                else "\x1b[31mfalse\x1b[0m"
                            )
                        elif isinstance(value, (int, float)):
                            display_value = f"\x1b[33m{value}\x1b[0m"
                        else:
                            display_value = str(value)
                if not is_object_node:
                    print(f"{prefix}{connector}{key}: {display_value}")

    def _log_user_profile(self, user: Dict):
        logger.info("-> User Data:")
        self._print_dynamic_tree(user)
