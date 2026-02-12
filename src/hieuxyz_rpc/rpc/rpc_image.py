import os
from abc import ABC, abstractmethod
from .image_service import ImageService
from typing import Optional

class RpcImage(ABC):
    """
    Base abstract class for all RPC image types.
    """
    
    @abstractmethod
    async def resolve(self, image_service: ImageService) -> Optional[str]:
        """
        Resolve the image into an asset key that Discord can understand.
        
        Args:
            image_service (ImageService): An instance of ImageService to handle uploads or proxies.
            
        Returns:
            Optional[str]: Asset key has been resolved.
        """
        pass

    @abstractmethod
    def get_cache_key(self) -> str:
        """
        Gets a unique key for this image instance, used for caching.
        
        Returns:
            str: A unique identifier for the image source.
        """
        pass

class DiscordImage(RpcImage):
    """
    Represents an image that already exists on Discord's servers (e.g., via proxy or previous upload).
    """
    def __init__(self, image_key: str):
        self.image_key = image_key

    async def resolve(self, image_service: ImageService) -> Optional[str]:
        return self.image_key if self.image_key.startswith('mp:') else f"mp:{self.image_key}"

    def get_cache_key(self) -> str:
        return f"discord:{self.image_key}"

class ExternalImage(RpcImage):
    """
    Represents an image from an external URL.
    """
    def __init__(self, url: str):
        self.url = url

    async def resolve(self, image_service: ImageService) -> Optional[str]:
        return await image_service.get_external_url(self.url)

    def get_cache_key(self) -> str:
        return f"external:{self.url}"

class LocalImage(RpcImage):
    """
    Represents an image from the local file system.
    Images will be uploaded via ImageService.
    """
    def __init__(self, file_path: str, file_name: Optional[str] = None):
        self.file_path = file_path
        self.file_name = file_name or os.path.basename(file_path)

    async def resolve(self, image_service: ImageService) -> Optional[str]:
        return await image_service.upload_image(self.file_path, self.file_name)

    def get_cache_key(self) -> str:
        return f"local:{self.file_path}"

class RawImage(RpcImage):
    """
    Represents a resolved raw asset key.
    No further processing required.
    """
    def __init__(self, asset_key: str):
        self.asset_key = asset_key

    async def resolve(self, image_service: ImageService) -> Optional[str]:
        return self.asset_key

    def get_cache_key(self) -> str:
        return f"raw:{self.asset_key}"

class ApplicationImage(RpcImage):
    """
    Represents an asset uploaded to the Discord Application (Bot Assets).
    It will resolve the asset ID by matching the asset name.
    """
    def __init__(self, asset_name: str):
        """
        Args:
            asset_name (str): The name of the asset as defined in the Discord Developer Portal.
        """
        self.asset_name = asset_name

    async def resolve(self, image_service: ImageService) -> Optional[str]:
        return f"app_asset:{self.asset_name}"

    def get_cache_key(self) -> str:
        return f"app_asset:{self.asset_name}"