import asyncio
import time
import re
from urllib.parse import urlparse
from typing import Optional, List, Dict, Union, Callable, Awaitable
from ..gateway.entities.types import ActivityType
from .image_service import ImageService
from .rpc_image import RpcImage, DiscordImage, ExternalImage, RawImage, ApplicationImage
from ..utils.logger import logger

UpdateCallback = Callable[[], Awaitable[None]]
DiscordPlatform = str  # 'desktop' | 'android' | 'ios' ...

class HieuxyzRPC:
    """
    Class built for creating and managing Discord Rich Presence states.
    """
    
    def __init__(self, image_service: ImageService, on_update: UpdateCallback):
        self.image_service = image_service
        self.on_update = on_update
        self.activity: Dict = {}
        self.assets: Dict = {}
        self.status = 'online'
        self.application_id = '1416676323459469363'
        self.platform: DiscordPlatform = 'desktop'
        self.resolved_assets_cache: Dict[str, str] = {}
        self.asset_message_ids: Dict[str, str] = {}
        self.MAX_CACHE_SIZE = 50
        self.application_assets_cache: Dict[str, Dict[str, str]] = {}
        self.renewal_task: Optional[asyncio.Task] = None
        self._start_background_renewal()

    @property
    def large_image_url(self) -> Optional[str]:
        """Returns the resolved URL for the large image, or None."""
        if 'large_image' not in self.assets or not self.assets['large_image']:
            return None
        cache_key = self.assets['large_image'].get_cache_key()
        resolved_asset = self.resolved_assets_cache.get(cache_key)
        return self._resolve_asset_url(resolved_asset) if resolved_asset else None

    @property
    def small_image_url(self) -> Optional[str]:
        """Returns the resolved URL for the small image, or None."""
        if 'small_image' not in self.assets or not self.assets['small_image']:
            return None
        cache_key = self.assets['small_image'].get_cache_key()
        resolved_asset = self.resolved_assets_cache.get(cache_key)
        return self._resolve_asset_url(resolved_asset) if resolved_asset else None

    @property
    def current_status(self) -> str:
        """Get the current status set for this RPC instance."""
        return self.status

    def _resolve_asset_url(self, asset_key: str) -> Optional[str]:
        if asset_key.startswith('mp:'):
            return f"https://media.discordapp.net/{asset_key[3:]}"
        if asset_key.startswith('spotify:'):
            return f"https://i.scdn.co/image/{asset_key[8:]}"
        if asset_key.startswith('youtube:'):
            return f"https://i.ytimg.com/vi/{asset_key[8:]}/hqdefault.jpg"
        if asset_key.startswith('twitch:'):
            return f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{asset_key[7:]}.png"
        if self.application_id and not asset_key.startswith('http'):
            return f"https://cdn.discordapp.com/app-assets/{self.application_id}/{asset_key}.png"
        return None

    def _to_rpc_image(self, source: Union[str, RpcImage]) -> RpcImage:
        if not isinstance(source, str):
            return source
        
        if source.startswith('https://') or source.startswith('http://'):
            try:
                url = urlparse(source)
                if url.hostname in ['cdn.discordapp.com', 'media.discordapp.net']:
                    discord_asset_path = url.path[1:]
                    return DiscordImage(discord_asset_path)
                else:
                    return ExternalImage(source)
            except:
                logger.warn(f'Could not parse "{source}" into a valid URL. Treating as RawImage.')
                return RawImage(source)
        
        if source.startswith('attachments/') or source.startswith('external/'):
            return DiscordImage(source)
        if re.match(r'^[a-zA-Z0-9_]+$', source) and not re.match(r'^\d{17,20}$', source):
            return ApplicationImage(source)
            
        return RawImage(source)

    def _cleanup_nulls(self, obj: Dict) -> Dict:
        return {k: v for k, v in obj.items() if v is not None}

    def _sanitize(self, s: str, length: int = 128) -> str:
        return s[:length] if len(s) > length else s

    def set_name(self, name: str) -> 'HieuxyzRPC':
        """Name the operation (first line of RPC)."""
        self.activity['name'] = self._sanitize(name)
        return self

    def set_details(self, details: str) -> 'HieuxyzRPC':
        """Set details for the operation (second line of RPC)."""
        self.activity['details'] = self._sanitize(details)
        return self

    def set_state(self, state: str) -> 'HieuxyzRPC':
        """Set the state for the operation (third line of the RPC)."""
        self.activity['state'] = self._sanitize(state)
        return self

    def set_type(self, type_val: Union[int, str]) -> 'HieuxyzRPC':
        """Set the activity type."""
        if isinstance(type_val, str):
            type_map = {
                'playing': ActivityType.Playing,
                'streaming': ActivityType.Streaming,
                'listening': ActivityType.Listening,
                'watching': ActivityType.Watching,
                'custom': ActivityType.Custom,
                'competing': ActivityType.Competing,
            }
            self.activity['type'] = type_map.get(type_val.lower(), ActivityType.Playing)
        else:
            self.activity['type'] = type_val
        return self

    def set_timestamps(self, start: Optional[int] = None, end: Optional[int] = None) -> 'HieuxyzRPC':
        """Set a start and/or end timestamp for the activity."""
        self.activity['timestamps'] = {'start': start, 'end': end}
        return self

    def set_party(self, current_size: int, max_size: int, id_val: str = 'hieuxyz') -> 'HieuxyzRPC':
        """Set party information for the activity."""
        self.activity['party'] = {'id': id_val, 'size': [current_size, max_size]}
        return self

    def set_large_image(self, source: Union[str, RpcImage], text: Optional[str] = None) -> 'HieuxyzRPC':
        """Set large image and its caption text."""
        self.assets['large_image'] = self._to_rpc_image(source)
        if text:
            self.assets['large_text'] = self._sanitize(text)
        return self

    def set_small_image(self, source: Union[str, RpcImage], text: Optional[str] = None) -> 'HieuxyzRPC':
        """Set the small image and its caption text."""
        self.assets['small_image'] = self._to_rpc_image(source)
        if text:
            self.assets['small_text'] = self._sanitize(text)
        return self

    def add_button(self, label: str, url: str) -> 'HieuxyzRPC':
        """Add a single button to the activity."""
        if 'buttons' not in self.activity:
            self.activity['buttons'] = []
        if 'metadata' not in self.activity:
            self.activity['metadata'] = {'button_urls': []}
        if 'button_urls' not in self.activity['metadata']:
            self.activity['metadata']['button_urls'] = []
            
        if len(self.activity['buttons']) >= 2:
            logger.warn('Cannot add more than 2 buttons. Button ignored.')
            return self
            
        self.activity['buttons'].append(self._sanitize(label, 32))
        self.activity['metadata']['button_urls'].append(url)
        return self

    def set_buttons(self, buttons: List[Dict[str, str]]) -> 'HieuxyzRPC':
        """Set clickable buttons for RPC (up to 2)."""
        valid_buttons = buttons[:2]
        self.activity['buttons'] = [self._sanitize(b['label'], 32) for b in valid_buttons]
        self.activity['metadata'] = {'button_urls': [b['url'] for b in valid_buttons]}
        return self

    def set_secrets(self, secrets: Dict) -> 'HieuxyzRPC':
        """Set secrets for joining, spectating, and matching games."""
        self.activity['secrets'] = secrets
        return self

    def set_sync_id(self, sync_id: str) -> 'HieuxyzRPC':
        """Set the sync_id, typically used for Spotify track synchronization."""
        self.activity['sync_id'] = sync_id
        return self

    def set_flags(self, flags: int) -> 'HieuxyzRPC':
        """Set activity flags."""
        self.activity['flags'] = flags
        return self

    def set_application_id(self, id_val: str) -> 'HieuxyzRPC':
        """Set custom application ID for RPC."""
        if not re.match(r'^\d{17,20}$', id_val):
            raise ValueError('The app ID must be a valid number string (17-20 digits).')
        self.application_id = id_val
        return self

    def set_status(self, status: str) -> 'HieuxyzRPC':
        """Set the user's status."""
        self.status = status
        return self

    def set_platform(self, platform: DiscordPlatform) -> 'HieuxyzRPC':
        """Set the platform on which the activity is running."""
        self.platform = platform
        return self

    def set_instance(self, instance: bool) -> 'HieuxyzRPC':
        """Marks the activity as a joinable instance for the game."""
        self.activity['instance'] = instance
        return self

    def clear_details(self) -> 'HieuxyzRPC':
        self.activity.pop('details', None)
        return self
    def clear_state(self) -> 'HieuxyzRPC':
        self.activity.pop('state', None)
        return self
    def clear_timestamps(self) -> 'HieuxyzRPC':
        self.activity.pop('timestamps', None)
        return self
    def clear_party(self) -> 'HieuxyzRPC':
        self.activity.pop('party', None)
        return self
    def clear_buttons(self) -> 'HieuxyzRPC':
        self.activity.pop('buttons', None)
        self.activity.pop('metadata', None)
        return self
    def clear_secrets(self) -> 'HieuxyzRPC':
        self.activity.pop('secrets', None)
        return self
    def clear_instance(self) -> 'HieuxyzRPC':
        self.activity.pop('instance', None)
        return self
    def clear_large_image(self) -> 'HieuxyzRPC':
        self.assets.pop('large_image', None)
        self.assets.pop('large_text', None)
        return self
    def clear_small_image(self) -> 'HieuxyzRPC':
        self.assets.pop('small_image', None)
        self.assets.pop('small_text', None)
        return self

    def _get_expiry_time(self, asset_key: str) -> Optional[int]:
        if not asset_key.startswith('mp:attachments'):
            return None
        url_part = asset_key[3:]
        try:
            url = urlparse(f"https://cdn.discordapp.com/{url_part}")
            params = {k: v for k, v in [p.split('=') for p in url.query.split('&') if '=' in p]}
            expires_timestamp = params.get('ex')
            if expires_timestamp:
                return int(expires_timestamp, 16) * 1000
        except Exception:
            logger.error(f"Could not parse asset URL for expiry check: {asset_key}")
        return None

    async def _renew_asset_if_needed(self, cache_key: str, asset_key: str) -> str:
        expiry_time_ms = self._get_expiry_time(asset_key)
        if expiry_time_ms and expiry_time_ms < (time.time() * 1000) + 3600000:
            # logger.info(f"Asset {cache_key} is expiring soon. Renewing...")
            message_id = self.asset_message_ids.get(cache_key)
            parts = asset_key.split('/')
            if message_id and len(parts) >= 4:
                channel_id = parts[1]
                filename = parts[-1].split('?')[0]
                renew_id = f"{channel_id}/{message_id}/{filename}"
                new_asset = await self.image_service.renew_image(renew_id)
                if new_asset:
                    self.resolved_assets_cache[cache_key] = new_asset
                    return new_asset
            else:
                logger.warn(f"Cannot renew asset: Message ID missing for {cache_key}")
                
            logger.warn("Failed to renew asset, will use the old one.")
        return asset_key

    def _start_background_renewal(self):
        async def renewal_loop():
            while True:
                await asyncio.sleep(600)
                # logger.info('Running background asset renewal check...')
                for cache_key, asset_key in list(self.resolved_assets_cache.items()):
                    await self._renew_asset_if_needed(cache_key, asset_key)
        if self.renewal_task:
            self.renewal_task.cancel()

        try:
            loop = asyncio.get_running_loop()
            self.renewal_task = loop.create_task(renewal_loop())
        except RuntimeError:
            pass

    def stop_background_renewal(self):
        if self.renewal_task:
            self.renewal_task.cancel()
            self.renewal_task = None

    async def _ensure_app_assets_loaded(self):
        if self.application_id not in self.application_assets_cache:
            logger.info(f"Fetching assets for Application ID: {self.application_id}...")
            assets = await self.image_service.fetch_application_assets(self.application_id)
            asset_map = {}
            for asset in assets:
                asset_map[asset['name']] = asset['id']
            self.application_assets_cache[self.application_id] = asset_map
            logger.info(f"Loaded {len(assets)} assets for Application ID: {self.application_id}.")

    async def _resolve_image(self, image: Optional[RpcImage]) -> Optional[str]:
        if not image:
            return None
        cache_key = image.get_cache_key()
        
        if cache_key.startswith('app_asset:'):
            await self._ensure_app_assets_loaded()
            asset_name = cache_key[len('app_asset:'):]
            app_assets = self.application_assets_cache.get(self.application_id)
            asset_id = app_assets.get(asset_name) if app_assets else None
            if not asset_id:
                logger.warn(f'Asset with name "{asset_name}" not found for Application ID {self.application_id}.')
                return None
            return asset_id

        if len(self.resolved_assets_cache) >= self.MAX_CACHE_SIZE and cache_key not in self.resolved_assets_cache:
            oldest_key = next(iter(self.resolved_assets_cache))
            del self.resolved_assets_cache[oldest_key]

        cached_asset = self.resolved_assets_cache.get(cache_key)
        if cached_asset:
            return await self._renew_asset_if_needed(cache_key, cached_asset)

        result = await image.resolve(self.image_service)
        if result and 'id' in result:
            asset_id = result['id']
            
            if 'message_id' in result and result['message_id']:
                self.asset_message_ids[cache_key] = result['message_id']

            if asset_id.startswith('app_asset:'):
                return await self._resolve_image(ApplicationImage(asset_id[10:]))
            
            self.resolved_assets_cache[cache_key] = asset_id
            return asset_id
        return None

    async def build_activity(self) -> Optional[Dict]:
        """
        Publicly accessible method to build the Activity object.
        """
        if not self.activity and not self.assets.get('large_image') and not self.assets.get('small_image'):
            return None

        large_image = await self._resolve_image(self.assets.get('large_image'))
        small_image = await self._resolve_image(self.assets.get('small_image'))

        final_assets = {
            'large_text': self.assets.get('large_text'),
            'small_text': self.assets.get('small_text')
        }
        if large_image:
            final_assets['large_image'] = large_image
        if small_image:
            final_assets['small_image'] = small_image

        final_activity = self.activity.copy()

        if large_image or small_image:
            final_activity['assets'] = final_assets
        
        final_activity['application_id'] = self.application_id
        final_activity['platform'] = self.platform
        
        if 'name' not in final_activity:
            final_activity['name'] = 'hieuxyzRPC'
        if 'type' not in final_activity:
            final_activity['type'] = ActivityType.Playing

        return self._cleanup_nulls(final_activity)

    async def build(self):
        """Builds and sends the presence payload to Discord."""
        await self.on_update()

    async def update_rpc(self):
        """Alias for build()."""
        await self.build()

    def clear(self):
        """Clears the Rich Presence from the user's profile and resets the builder."""
        self.activity = {}
        self.assets = {}
        self.application_id = '1416676323459469363'
        self.platform = 'desktop'
        logger.info('RPC instance cleared.')
        loop = asyncio.get_running_loop()
        loop.create_task(self.on_update())

    def clear_cache(self):
        """Manually clear the asset cache to free memory."""
        self.resolved_assets_cache.clear()
        self.application_assets_cache.clear()
        self.asset_message_ids.clear()
        logger.info('RPC Asset cache has been cleared.')

    def destroy(self):
        """Permanently destroy this RPC instance."""
        self.stop_background_renewal()
        self.clear_cache()
        self.activity = {}
        self.assets = {}