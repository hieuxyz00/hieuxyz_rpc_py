# hieuxyz-rpc

> A powerful Discord Rich Presence library for Python.
> **Note:** This project is a Python port of the library [@hieuxyz/rpc](https://github.com/hieuxyz00/hieuxyz_rpc).

[![PyPI version](https://badge.fury.io/py/hieuxyz-rpc.svg)](https://badge.fury.io/py/hieuxyz-rpc)
[![License](https://img.shields.io/badge/license-ISC-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

`hieuxyz-rpc` allows you to control the RPC status of a Discord **User Account** directly from Python. It supports advanced features like multi-RPC, client spoofing, custom assets, and buttons.

> [!WARNING]
> **I do not take responsibility for any blocked Discord accounts resulting from the use of this library.**

> [!CAUTION]
> **Using this on a User Account is against the [Discord Terms of Service](https://discord.com/terms) (Self-botting) and may lead to account termination.**
> **By using this library, you accept the risk involved in exposing your Discord Token.**

## Installation

Install using pip:

```bash
pip install hieuxyz-rpc
```

## Usage

### Basic Example

```python
import asyncio
import os
import time
from hieuxyz_rpc import Client, ClientOptions, logger

async def main():
    token = "YOUR_DISCORD_USER_TOKEN"

    # Initialize Client
    client = Client(ClientOptions(
        token=token,
        always_reconnect=True
    ))

    # Connect to Gateway
    await client.run()

    # Configure RPC
    (client.rpc
        .set_name('Visual Studio Code')
        .set_details('Editing main.py')
        .set_state('Workspace: hieuxyz-rpc')
        .set_platform('desktop')
        .set_type(0) # Playing
        .set_timestamps(int(time.time() * 1000))
        .set_party(1, 5)
        .set_application_id('914622396630175855')
        .set_large_image('python_icon', 'Python')
        .set_small_image('vscode', 'VS Code')
        .set_buttons([
            { 'label': 'View on GitHub', 'url': 'https://github.com/hieuxyz00/hieuxyz_rpc' },
            { 'label': 'View on PyPI', 'url': 'https://pypi.org/project/hieuxyz-rpc/' },
        ]))

    # Send update to Discord
    await client.rpc.build()
    logger.info('Rich Presence updated!')

    # Keep the script running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        client.close(True)

if __name__ == '__main__':
    asyncio.run(main())
```

## Advanced Usage

### Client Spoofing (Mobile/Console Status)

You can make it appear as though you are using Discord from a different device (e.g., smartphone, Xbox) by providing `properties` in `ClientOptions`.

```python
from hieuxyz_rpc import Client, ClientOptions

client = Client(ClientOptions(
    token="YOUR_TOKEN",
    properties={
        "os": "Android",
        "browser": "Discord Android",
        "device": "Android16"
    }
))
```

### Multi-RPC

You can display multiple statuses at once (e.g. Playing a game AND Listening to Spotify).

```python
# Update default RPC
client.rpc.set_name("Coding").set_type(0) # Playing

# Create a second RPC instance
music_rpc = client.create_rpc()
music_rpc.set_name("Spotify") \
         .set_details("Listening to Lo-Fi") \
         .set_type(2) \
         .set_application_id("12345678901234567") # Must use a different App ID

# Send all activities
await client.rpc.build() # Or client.send_all_activities() internally
```

## API Reference

### Class `Client`

- `Client(options: ClientOptions)`: Create a new instance.
- `await client.run()`: Connects to Discord Gateway.
- `client.rpc`: Access the default `HieuxyzRPC` builder.
- `client.create_rpc()`: Creates a new `HieuxyzRPC` instance.
- `client.close(force: bool)`: Closes the connection.

### Class `HieuxyzRPC`

Builder class for Rich Presence. Methods are chainable.

- `.set_name(str)`: Activity name.
- `.set_details(str)`: Activity details.
- `.set_state(str)`: Activity state.
- `.set_type(int | str)`: 0/playing, 1/streaming, 2/listening, 3/watching, 5/competing.
- `.set_timestamps(start, end)`: Unix timestamps in ms.
- `.set_party(current, max, id)`: Set party size and ID.
- `.set_large_image(source, text)`: `source` can be URL, Asset Key, or `RpcImage`.
- `.set_small_image(source, text)`: Same as above.
- `.set_buttons(list[dict])`: List of `{'label': '...', 'url': '...'}`.
- `.add_button(label, url)`: Add a single button.
- `.set_application_id(str)`: Custom App ID.
- `.set_platform(str)`: 'desktop', 'android', 'ios', 'xbox', etc.
- `.set_flags(int)`: Set activity flags.
- `.set_secrets(dict)`: Set secrets for game invites.
- `.build() / .update_rpc()`: Sends the payload to Discord.
- `.clear()`: Resets the RPC state.

## Author

- Developed by **hieuxyz**
- GitHub: [@hieuxyz00](https://github.com/hieuxyz00)

## License

ISC License