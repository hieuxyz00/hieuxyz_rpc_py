import asyncio
import json
import zlib
import random
import aiohttp
from typing import Optional, Dict, Any
from ..utils.logger import logger
from .entities.identify import get_identify_payload, ClientProperties
from .entities.opcode import OpCode
from .entities.types import DiscordUser

class DiscordWebSocketOptions:
    def __init__(self, always_reconnect: bool, properties: Optional[ClientProperties], connection_timeout: int):
        self.always_reconnect = always_reconnect
        self.properties = properties
        self.connection_timeout = connection_timeout

class DiscordWebSocket:
    """
    Manage WebSocket connections to Discord Gateway.
    Handles low-level operations like heartbeating, identifying, and resuming.
    """
    def __init__(self, token: str, options: DiscordWebSocketOptions):
        if not self._is_token_valid(token):
            raise ValueError('Invalid token provided.')
        
        self.token = token
        self.options = options
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.sequence: Optional[int] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
        self.heartbeat_interval_value: int = 0
        self.session_id: Optional[str] = None
        self.resume_gateway_url: Optional[str] = None
        self.is_reconnecting = False
        self.permanent_close = False
        self.connect_timeout_task: Optional[asyncio.Task] = None
        self.last_heartbeat_ack = True
        self.user: Optional[DiscordUser] = None
        self.ready_future = asyncio.Future()
        self._buffer = bytearray()
        self._zlib = zlib.decompressobj()

    def _reset_ready_future(self):
        self.ready_future = asyncio.Future()

    def _is_token_valid(self, token: str) -> bool:
        return len(token.split('.')) >= 3

    async def connect(self):
        """
        Initiate connection to Discord Gateway.
        """
        if self.is_reconnecting:
            logger.info('Connection attempt aborted: reconnection already in progress.')
            return
        self.permanent_close = False
        self.is_reconnecting = True
        self._reset_ready_future()
        if self.session and not self.session.closed:
            await self.session.close()
        url = self.resume_gateway_url or 'wss://gateway.discord.gg/?v=10&encoding=json&compress=zlib-stream'
        logger.info(f"Attempting to connect to {url}...")
        self.session = aiohttp.ClientSession()
        
        try:
            async def _connect_with_timeout():
                try:
                    self.ws = await self.session.ws_connect(url)
                    logger.info(f"Successfully connected to Discord Gateway at {url}.")
                    self.is_reconnecting = False
                except Exception as e:
                    logger.error(f"WebSocket Connection Error: {e}")
                    raise
            await asyncio.wait_for(_connect_with_timeout(), timeout=self.options.connection_timeout / 1000)
            if self.listen_task:
                self.listen_task.cancel()
            self.listen_task = asyncio.create_task(self._listen())
        except asyncio.TimeoutError:
            logger.error('Connection timed out. Terminating connection attempt.')
            if self.ws:
                await self.ws.close()
            await self.session.close()
        except Exception as e:
            if not self.is_reconnecting:
                 logger.error(f"Connection failed: {e}")

    async def _listen(self):
        """Listen for msg from WebSocket."""
        if not self.ws: return
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    self._buffer.extend(msg.data)
                    if len(self._buffer) < 4 or self._buffer[-4:] != b'\x00\x00\xff\xff':
                        continue
                    
                    try:
                        decompressed_data = self._zlib.decompress(self._buffer)
                        decompressed_data = decompressed_data.decode('utf-8')
                        self._buffer = bytearray()
                        payload = json.loads(decompressed_data)
                        await self._on_message(payload)
                    except Exception as e:
                        logger.error(f"Decompression/Parse Error: {e}")
                        self._buffer = bytearray()
                        self._zlib = zlib.decompressobj()
                elif msg.type == aiohttp.WSMsgType.TEXT:
                     payload = json.loads(msg.data)
                     await self._on_message(payload)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception as e:
            # logger.error(f"Error in listen loop: {e}")
            pass
        finally:
            close_code = self.ws.close_code or 1000
            if not self.ws.closed:
                 logger.warn(f"Connection closed: {close_code}")
            await self._handle_close(close_code)

    async def _handle_close(self, code: int):
        self._cleanup_heartbeat()
        self.is_reconnecting = False
        self._buffer = bytearray()
        self._zlib = zlib.decompressobj()

        if code in [4004, 4999]:
            self.session_id = None
            self.sequence = None
            self.resume_gateway_url = None
        
        if self.permanent_close:
            logger.info('Connection permanently closed by client. Not reconnecting.')
            if self.session: await self.session.close()
            return

        if self._should_reconnect(code):
            logger.info('Attempting to reconnect in 5 seconds...')
            if self.session: await self.session.close()
            await asyncio.sleep(5)
            await self.connect()
        else:
            logger.info('Not attempting to reconnect based on close code and client options.')
            if self.session: await self.session.close()

    async def _on_message(self, payload: Dict[str, Any]):
        op = payload.get('op')
        d = payload.get('d')
        s = payload.get('s')
        t = payload.get('t')

        if s:
            self.sequence = s

        if op == OpCode.HELLO:
            self.heartbeat_interval_value = d['heartbeat_interval']
            logger.info(f"Received HELLO. Setting heartbeat interval to {self.heartbeat_interval_value}ms.")
            self._start_heartbeating()
            
            if self.session_id and self.sequence:
                await self._resume()
            else:
                await self._identify()

        elif op == OpCode.DISPATCH:
            if t == 'READY':
                self.session_id = d['session_id']
                self.resume_gateway_url = d['resume_gateway_url'].rstrip('/') + '/?v=10&encoding=json&compress=zlib-stream'
                self.user = d['user'] 
                
                logger.info(f"Session READY. Session ID: {self.session_id}. Resume URL set.")
                if not self.ready_future.done():
                    self.ready_future.set_result(self.user)
            elif t == 'RESUMED':
                logger.info('The session has been successfully resumed.')
                if self.user and not self.ready_future.done():
                    self.ready_future.set_result(self.user)

        elif op == OpCode.HEARTBEAT_ACK:
            logger.info('Heartbeat acknowledged.')
            self.last_heartbeat_ack = True

        elif op == OpCode.INVALID_SESSION:
            logger.warn(f"Received INVALID_SESSION. Resumable: {d}")
            if d:
                if self.ws: await self.ws.close(code=4000, message=b'Invalid session, attempting to resume.')
            else:
                self.session_id = None
                self.sequence = None
                if self.ws: await self.ws.close(code=4004, message=b'Invalid session, starting a new session.')

        elif op == OpCode.RECONNECT:
            logger.info('Gateway requested RECONNECT. Closing to reconnect and resume.')
            if self.ws: await self.ws.close(code=4000, message=b'Gateway requested reconnect.')
        
        elif op == OpCode.HEARTBEAT:
            await self._send_heartbeat()

    def _start_heartbeating(self):
        self._cleanup_heartbeat()
        self.last_heartbeat_ack = True
        
        async def heartbeat_loop():
            jitter = self.heartbeat_interval_value * random.random()
            await asyncio.sleep(jitter / 1000)
            if self.ws and not self.ws.closed:
                await self._send_heartbeat()
            while True:
                await asyncio.sleep(self.heartbeat_interval_value / 1000)
                
                if not self.last_heartbeat_ack:
                    logger.warn('Heartbeat ACK missing. Connection is zombie. Terminating to resume...')
                    if self.ws: await self.ws.close()
                    break
                
                if not self.ws or self.ws.closed:
                    logger.warn('Heartbeat skipped: WebSocket is not open.')
                    break

                self.last_heartbeat_ack = False
                await self._send_heartbeat()

        self.heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def _send_heartbeat(self):
        if not self.ws or self.ws.closed: return
        await self._send_json({'op': OpCode.HEARTBEAT, 'd': self.sequence})
        logger.info(f"Heartbeat sent with sequence {self.sequence}.")

    async def _identify(self):
        identify_payload = get_identify_payload(self.token, self.options.properties)
        await self._send_json({'op': OpCode.IDENTIFY, 'd': identify_payload})
        logger.info('Identify payload sent.')

    async def _resume(self):
        if not self.session_id or self.sequence is None:
            logger.error('Attempted to resume without session ID or sequence. Falling back to identify.')
            await self._identify()
            return
        
        resume_payload = {
            'token': self.token,
            'session_id': self.session_id,
            'seq': self.sequence,
        }
        await self._send_json({'op': OpCode.RESUME, 'd': resume_payload})
        logger.info('Resume payload sent.')

    async def send_activity(self, presence: Dict):
        """Send presence update payload to Gateway."""
        await self._send_json({'op': OpCode.PRESENCE_UPDATE, 'd': presence})
        logger.info('Presence update sent.')

    async def _send_json(self, data: Dict):
        if self.ws and not self.ws.closed:
            await self.ws.send_json(data)
        else:
            logger.warn('Attempted to send data while WebSocket was not open.')

    async def close(self, force: bool = False):
        """Closes the WebSocket connection."""
        if force:
            logger.info('Forcing permanent closure. Reconnects will be disabled.')
            self.permanent_close = True
        else:
            logger.info('Closing connection manually...')
        
        if self.listen_task:
            self.listen_task.cancel()
        
        self._cleanup_heartbeat()

        if self.ws:
            await self.ws.close(code=1000, message=b'Client initiated closure')
        if self.session:
            await self.session.close()

    def _cleanup_heartbeat(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

    def _should_reconnect(self, code: int) -> bool:
        fatal_error_codes = [4004, 4010, 4011, 4013, 4014]
        if code in fatal_error_codes:
            logger.error(f"Fatal WebSocket error received (code: {code}). Will not reconnect.")
            return False
        if self.options.always_reconnect:
            return True
        return code != 1000