from typing import Optional, TypedDict

class ClientProperties(TypedDict, total=False):
    """
    Client properties to send to Discord gateway.
    
    Attributes:
        os (str): The operating system. (e.g., 'Windows', 'Android')
        browser (str): The browser or client. (e.g., 'Discord Client', 'Discord Android')
        device (str): The device. (e.g., 'Android16')
    """
    os: Optional[str]
    browser: Optional[str]
    device: Optional[str]

def get_identify_payload(token: str, properties: Optional[ClientProperties] = None) -> dict:
    default_properties = {
        "os": "Windows",
        "browser": "Discord Client",
        "device": "hieuxyz©rpc",
    }
    
    final_properties = default_properties.copy()
    if properties:
        final_properties.update({k: v for k, v in properties.items() if v is not None})

    return {
        "token": token,
        "capabilities": 65,
        "largeThreshold": 50,
        "properties": final_properties,
        "compress": True,
    }