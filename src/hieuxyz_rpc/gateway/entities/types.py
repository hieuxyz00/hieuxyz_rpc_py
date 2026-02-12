from enum import IntEnum, IntFlag
from typing import TypedDict, Optional, List, Dict, Any, Union

class ActivityType(IntEnum):
    Playing = 0
    Streaming = 1
    Listening = 2
    Watching = 3
    Custom = 4
    Competing = 5

class UserFlags(IntFlag):
    STAFF = 1 << 0
    PARTNER = 1 << 1
    HYPESQUAD = 1 << 2
    BUG_HUNTER_LEVEL_1 = 1 << 3
    HYPESQUAD_ONLINE_HOUSE_1 = 1 << 6  # Bravery
    HYPESQUAD_ONLINE_HOUSE_2 = 1 << 7  # Brilliance
    HYPESQUAD_ONLINE_HOUSE_3 = 1 << 8  # Balance
    PREMIUM_EARLY_SUPPORTER = 1 << 9
    TEAM_PSEUDO_USER = 1 << 10
    BUG_HUNTER_LEVEL_2 = 1 << 14
    VERIFIED_BOT = 1 << 16
    VERIFIED_DEVELOPER = 1 << 17
    CERTIFIED_MODERATOR = 1 << 18
    BOT_HTTP_INTERACTIONS = 1 << 19
    ACTIVE_DEVELOPER = 1 << 22

class ActivityFlags(IntFlag):
    INSTANCE = 1 << 0
    JOIN = 1 << 1
    SPECTATE = 1 << 2
    JOIN_REQUEST = 1 << 3
    SYNC = 1 << 4
    PLAY = 1 << 5

class DiscordUser(TypedDict, total=False):
    """
    Represents a Discord User structure from the Gateway.
    Using total=False to allow optional fields without strict checks at runtime.
    """
    id: str
    username: str
    discriminator: str
    global_name: Optional[str]
    avatar: Optional[str]
    bot: Optional[bool]
    system: Optional[bool]
    mfa_enabled: Optional[bool]
    banner: Optional[str]
    accent_color: Optional[int]
    locale: Optional[str]
    verified: Optional[bool]
    email: Optional[str]
    flags: Optional[int]
    premium_type: Optional[int]  # 0: None, 1: Nitro Classic, 2: Nitro, 3: Nitro Basic
    public_flags: Optional[int]
    bio: Optional[str]
    phone: Optional[str]
    nsfw_allowed: Optional[bool]
    pronouns: Optional[str]
    mobile: Optional[bool]
    desktop: Optional[bool]
    clan: Optional[Dict[str, Any]]
    primary_guild: Optional[Dict[str, Any]]
    purchased_flags: Optional[int]
    premium_usage_flags: Optional[int]
    premium: Optional[bool]
    premium_state: Optional[Dict[str, Any]]
    avatar_decoration_data: Optional[Dict[str, Any]]
    collectibles: Optional[Dict[str, Any]]
    display_name_styles: Optional[Dict[str, Any]]
    banner_color: Optional[str]
    age_verification_status: Optional[int]

class ActivityParty(TypedDict, total=False):
    id: Optional[str]
    size: Optional[List[int]]  # [current, max]

class ActivityTimestamps(TypedDict, total=False):
    start: Optional[int]
    end: Optional[int]

class ActivityAssets(TypedDict, total=False):
    large_image: Optional[str]
    large_text: Optional[str]
    small_image: Optional[str]
    small_text: Optional[str]

class ActivitySecrets(TypedDict, total=False):
    join: Optional[str]
    spectate: Optional[str]
    match: Optional[str]

class ActivityMetadata(TypedDict, total=False):
    button_urls: Optional[List[str]]

class Activity(TypedDict, total=False):
    name: str
    type: int
    application_id: Optional[str]
    details: Optional[str]
    state: Optional[str]
    platform: Optional[str]
    instance: Optional[bool]
    flags: Optional[int]
    sync_id: Optional[str]
    party: Optional[ActivityParty]
    timestamps: Optional[ActivityTimestamps]
    assets: Optional[ActivityAssets]
    secrets: Optional[ActivitySecrets]
    buttons: Optional[List[str]]
    metadata: Optional[ActivityMetadata]

class PresenceUpdatePayload(TypedDict):
    since: int
    activities: List[Activity]
    status: str # 'online' | 'dnd' | 'idle' | 'invisible' | 'offline'
    afk: bool