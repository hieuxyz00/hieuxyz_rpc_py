import asyncio
import os
import sys
import time
import signal
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src'))) # for run locally without installing via pip.

from hieuxyz_rpc import Client, ClientOptions, logger

load_dotenv()

async def main():
    token = os.getenv('DISCORD_USER_TOKEN')
    if not token:
        logger.error('Token not found in .env file. Please set DISCORD_USER_TOKEN.')
        return

    client = Client(ClientOptions(
        token=token,
        always_reconnect=True
    ))

    try:
        await client.run()

        (client.rpc
            .set_name('Visual Studio Code')
            .set_details('Update rpc library')
            .set_state('Workspace: @hieuxyz/rpc')
            .set_platform('desktop')
            .set_type(0) # 0: Playing
            .set_timestamps(int(time.time() * 1000))
            .set_party(1, 5)
            .set_application_id('914622396630175855')
            .set_large_image('ts_file')
            .set_small_image('vs_2026')
            .set_buttons([
                { 'label': 'View on GitHub', 'url': 'https://github.com/hieuxyz00/hieuxyz_rpc' },
                { 'label': 'View on NPM', 'url': 'https://www.npmjs.com/package/@hieuxyz/rpc' },
            ]))

        await client.rpc.build()
        logger.info('Initial Rich Presence has been updated. Check your Discord profile.')
        logger.info('An update will occur in 15 seconds. Press Ctrl+C to exit.')

        async def update_task():
            try:
                await asyncio.sleep(15)
                logger.info('Updating RPC details dynamically...')
                
                client.rpc.set_details('Idle').set_state('Waiting...').set_party(2, 5)
                await client.rpc.update_rpc()
                
                logger.info('RPC has been dynamically updated. Check your Discord profile again!')
            except asyncio.CancelledError:
                pass
        background_task = asyncio.create_task(update_task())
        stop_event = asyncio.Event()
        if os.name != 'nt':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: stop_event.set())
        if os.name == 'nt':
            while True:
                await asyncio.sleep(1)
        else:
            await stop_event.wait()

    except asyncio.CancelledError:
        logger.info("Tasks cancelled.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        logger.info('Closing connection...')
        client.close(force=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program stopped by user (Ctrl+C).")