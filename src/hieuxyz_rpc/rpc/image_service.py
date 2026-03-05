import os
import aiohttp
from ..utils.logger import logger
from typing import Optional, List, Dict, Any


class ImageService:
    """
    A service to handle external image proxying and local image uploading.
    Interact with a backend API service to manage image assets.
    """

    def __init__(self, api_base_url: Optional[str] = None):
        """
        Create an ImageService instance.

        Args:
            api_base_url (str): The base URL of the image upload/proxy API.
        """
        self.api_base_url = api_base_url or "https://rpc.hieuxyz.fun"

    async def get_external_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Get an asset key proxy for an external image URL.

        Args:
            url (str): URL of external image.

        Returns:
            Optional[Dict]: Asset key resolved (id) or None if failed.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base_url}/image", params={"url": url}
                ) as response:
                    data = await response.json()
                    if data and data.get("status") == 200 and "id" in data:
                        return {"id": data["id"]}
        except Exception as error:
            logger.error(f"Unable to get external proxy URL for {url}: {error}")
        return None

    async def upload_image(
        self, file_path: str, file_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Upload an image from the local file system to the image service.

        Args:
            file_path (str): Path to the image file.
            file_name (str): File name to use when uploading.

        Returns:
            Optional[Dict]: Dict with 'id' and 'message_id' or None if failed.
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found at path: {file_path}")
                return None

            data = aiohttp.FormData()
            data.add_field("file", open(file_path, "rb"), filename=file_name)
            data.add_field("file_name", file_name)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/upload", data=data
                ) as response:
                    res_data = await response.json()
                    if res_data and res_data.get("status") == 200 and "id" in res_data:
                        return {
                            "id": res_data["id"],
                            "message_id": res_data.get("message_id"),
                        }
        except Exception as error:
            logger.error(f"Unable to upload image {file_name}: {error}")
        return None

    async def renew_image(self, asset_id: str) -> Optional[str]:
        """
        Requests a new signed URL for an expired or expiring attachment asset.

        Args:
            asset_id (str): The asset ID part of the URL.

        Returns:
            Optional[str]: The new asset key or None if it failed.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base_url}/renew", json={"asset_id": asset_id}
                ) as response:
                    data = await response.json()
                    if data and data.get("status") == 200 and "id" in data:
                        logger.info(f"Successfully renewed asset: {asset_id}")
                        return data["id"]
        except Exception as error:
            logger.error(f"Failed to renew asset {asset_id}: {error}")
        return None

    async def fetch_application_assets(
        self, application_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all assets for a specific Discord Application.

        Args:
            application_id (str): The ID of the application.

        Returns:
            List[Dict]: List of assets (id, name, type).
        """
        try:
            url = f"https://discord.com/api/v9/oauth2/applications/{application_id}/assets"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
        except Exception as error:
            logger.error(
                f"Failed to fetch assets for application {application_id}: {error}. Ensure the App ID is correct."
            )
            return []

