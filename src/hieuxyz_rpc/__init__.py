__VERSION__ = "0.0.2"
__AUTHOR__ = "hieuxyz"
from .client import Client, ClientOptions
from .gateway.discord_websocket import DiscordWebSocket
from .rpc.hieuxyz_rpc import HieuxyzRPC
from .rpc.image_service import ImageService
from .rpc.rpc_image import (
    RpcImage,
    DiscordImage,
    ExternalImage,
    LocalImage,
    RawImage,
    ApplicationImage,
)
from .utils.logger import logger
from .gateway.entities.types import ActivityType
