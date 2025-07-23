"""
MCP Protocol implementation for communication with AI models.
Based on the actual MCP (Model Context Protocol) specification.
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """MCP protocol message structure"""
    jsonrpc: str = "2.0"
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.method is not None:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )


@dataclass
class MCPRequest(MCPMessage):
    """MCP request message"""
    def __init__(self, method: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(method=method, params=params or {})


@dataclass
class MCPResponse(MCPMessage):
    """MCP response message"""
    def __init__(self, id: str, result: Any = None, error: Dict[str, Any] = None):
        super().__init__(id=id, result=result, error=error)


class MCPError(Exception):
    """MCP protocol error"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


class MCPConnection:
    """Manages MCP protocol communication"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.notification_handlers: Dict[str, List[Callable]] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._closed = False
    
    async def start(self):
        """Start reading messages"""
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._read_loop())
    
    async def close(self):
        """Close the connection"""
        self._closed = True
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        self.writer.close()
        await self.writer.wait_closed()
    
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, 
                          timeout: Optional[float] = None) -> Any:
        """Send a request and wait for response"""
        request = MCPRequest(method, params)
        future = asyncio.Future()
        self.pending_requests[request.id] = future
        
        try:
            await self._send_message(request)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request.id, None)
            raise MCPError(-32000, f"Request timeout for method: {method}")
        except Exception as e:
            self.pending_requests.pop(request.id, None)
            raise
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a notification (no response expected)"""
        notification = MCPMessage(method=method, params=params)
        notification.id = None  # Notifications have no ID
        await self._send_message(notification)
    
    def on_notification(self, method: str, handler: Callable):
        """Register a notification handler"""
        if method not in self.notification_handlers:
            self.notification_handlers[method] = []
        self.notification_handlers[method].append(handler)
    
    async def _send_message(self, message: MCPMessage):
        """Send a message over the connection"""
        if self._closed:
            raise MCPError(-32000, "Connection is closed")
        
        data = json.dumps(message.to_dict()) + "\n"
        self.writer.write(data.encode('utf-8'))
        await self.writer.drain()
        
        logger.debug(f"Sent message: {message.method or 'response'}")
    
    async def _read_loop(self):
        """Continuously read messages from the connection"""
        try:
            while not self._closed:
                line = await self.reader.readline()
                if not line:
                    break
                
                try:
                    data = json.loads(line.decode('utf-8').strip())
                    message = MCPMessage.from_dict(data)
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Read loop error: {e}")
        finally:
            # Clean up pending requests
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(MCPError(-32000, "Connection closed"))
    
    async def _handle_message(self, message: MCPMessage):
        """Handle an incoming message"""
        if message.id and message.id in self.pending_requests:
            # This is a response to our request
            future = self.pending_requests.pop(message.id)
            if message.error:
                future.set_exception(MCPError(
                    message.error.get('code', -32000),
                    message.error.get('message', 'Unknown error'),
                    message.error.get('data')
                ))
            else:
                future.set_result(message.result)
        elif message.method:
            # This is a notification
            handlers = self.notification_handlers.get(message.method, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message.params)
                    else:
                        handler(message.params)
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")


class MCPClient:
    """High-level MCP client"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.connection: Optional[MCPConnection] = None
    
    async def connect(self) -> MCPConnection:
        """Establish connection to MCP server"""
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self.connection = MCPConnection(reader, writer)
        await self.connection.start()
        
        # Send initialization
        await self.connection.send_request("initialize", {
            "protocolVersion": "1.0",
            "clientInfo": {
                "name": "miszen",
                "version": "0.1.0"
            }
        })
        
        logger.info(f"Connected to MCP server at {self.host}:{self.port}")
        return self.connection
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Disconnected from MCP server")