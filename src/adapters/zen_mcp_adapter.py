"""
Zen-MCP adapter for integrating zen-MCP commands with MIS.
Provides abstraction layer for all 15 zen-MCP commands.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..core.mcp_protocol import MCPClient, MCPConnection, MCPError
from ..core.config import config


logger = logging.getLogger(__name__)


@dataclass
class ZenCommandResult:
    """Result from a zen-MCP command execution"""
    command: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ZenMCPAdapter:
    """Adapter for zen-MCP commands"""
    
    # Command categories for better organization
    CHAT_COMMANDS = ['chat', 'challenge', 'consensus']
    ANALYSIS_COMMANDS = ['analyze', 'thinkdeep', 'tracer']
    DEVELOPMENT_COMMANDS = ['codereview', 'refactor', 'testgen', 'docgen']
    WORKFLOW_COMMANDS = ['planner', 'precommit', 'debug', 'secaudit']
    UTILITY_COMMANDS = ['listmodels', 'version']
    
    def __init__(self):
        self.client: Optional[MCPClient] = None
        self.connection: Optional[MCPConnection] = None
        self._connected = False
        self._command_history: List[ZenCommandResult] = []
    
    async def connect(self) -> bool:
        """Connect to zen-MCP server"""
        try:
            self.client = MCPClient(config.mcp.host, config.mcp.port)
            self.connection = await self.client.connect()
            self._connected = True
            logger.info("Successfully connected to zen-MCP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to zen-MCP: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from zen-MCP server"""
        if self.client:
            await self.client.disconnect()
        self._connected = False
        logger.info("Disconnected from zen-MCP server")
    
    async def execute_command(self, command: str, params: Dict[str, Any]) -> ZenCommandResult:
        """Execute a zen-MCP command"""
        if not self._connected:
            raise RuntimeError("Not connected to zen-MCP server")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get command-specific timeout
            timeout = config.get_zen_command_timeout(command)
            
            # Add default parameters if not provided
            if 'model' not in params:
                params['model'] = self._get_default_model(command)
            
            # Execute command
            result = await self.connection.send_request(
                f"zen__{command}",
                params,
                timeout=timeout
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            command_result = ZenCommandResult(
                command=command,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
            self._command_history.append(command_result)
            logger.info(f"Successfully executed {command} in {execution_time:.2f}s")
            
            return command_result
            
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Command {command} timed out after {timeout}s"
            
            command_result = ZenCommandResult(
                command=command,
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
            
            self._command_history.append(command_result)
            logger.error(error_msg)
            
            return command_result
            
        except MCPError as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"MCP error in {command}: {e.message}"
            
            command_result = ZenCommandResult(
                command=command,
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
            
            self._command_history.append(command_result)
            logger.error(error_msg)
            
            return command_result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = f"Unexpected error in {command}: {str(e)}"
            
            command_result = ZenCommandResult(
                command=command,
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
            
            self._command_history.append(command_result)
            logger.error(error_msg, exc_info=True)
            
            return command_result
    
    def _get_default_model(self, command: str) -> str:
        """Get default model for a command based on its requirements"""
        # High-complexity commands that need advanced models
        if command in ['thinkdeep', 'secaudit', 'consensus']:
            return 'gemini-2.5-pro'
        # Fast commands that need quick responses
        elif command in ['chat', 'listmodels', 'version']:
            return 'gemini-2.5-flash'
        # Default for most development commands
        else:
            return 'o3-mini'
    
    async def chat(self, prompt: str, **kwargs) -> ZenCommandResult:
        """Execute chat command for general conversation"""
        params = {'prompt': prompt, **kwargs}
        return await self.execute_command('chat', params)
    
    async def analyze(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute analyze command for code analysis"""
        params = {'step': step, **kwargs}
        return await self.execute_command('analyze', params)
    
    async def debug(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute debug command for debugging assistance"""
        params = {'step': step, **kwargs}
        return await self.execute_command('debug', params)
    
    async def thinkdeep(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute thinkdeep for complex problem solving"""
        params = {'step': step, **kwargs}
        return await self.execute_command('thinkdeep', params)
    
    async def planner(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute planner for project planning"""
        params = {'step': step, **kwargs}
        return await self.execute_command('planner', params)
    
    async def codereview(self, step: str, files: List[str], **kwargs) -> ZenCommandResult:
        """Execute codereview for code review"""
        params = {'step': step, 'relevant_files': files, **kwargs}
        return await self.execute_command('codereview', params)
    
    async def refactor(self, step: str, files: List[str], **kwargs) -> ZenCommandResult:
        """Execute refactor for code refactoring"""
        params = {'step': step, 'relevant_files': files, **kwargs}
        return await self.execute_command('refactor', params)
    
    async def testgen(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute testgen for test generation"""
        params = {'step': step, **kwargs}
        return await self.execute_command('testgen', params)
    
    async def docgen(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute docgen for documentation generation"""
        params = {'step': step, **kwargs}
        return await self.execute_command('docgen', params)
    
    async def challenge(self, prompt: str) -> ZenCommandResult:
        """Execute challenge for critical thinking"""
        params = {'prompt': prompt}
        return await self.execute_command('challenge', params)
    
    async def consensus(self, step: str, models: List[Dict[str, str]], **kwargs) -> ZenCommandResult:
        """Execute consensus for multi-model consensus"""
        params = {'step': step, 'models': models, **kwargs}
        return await self.execute_command('consensus', params)
    
    async def precommit(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute precommit for pre-commit validation"""
        params = {'step': step, **kwargs}
        return await self.execute_command('precommit', params)
    
    async def tracer(self, target_description: str, **kwargs) -> ZenCommandResult:
        """Execute tracer for code tracing"""
        params = {'target_description': target_description, **kwargs}
        return await self.execute_command('tracer', params)
    
    async def secaudit(self, step: str, **kwargs) -> ZenCommandResult:
        """Execute secaudit for security audit"""
        params = {'step': step, **kwargs}
        return await self.execute_command('secaudit', params)
    
    async def listmodels(self) -> ZenCommandResult:
        """List available AI models"""
        return await self.execute_command('listmodels', {})
    
    async def version(self) -> ZenCommandResult:
        """Get zen-MCP version information"""
        return await self.execute_command('version', {})
    
    def get_command_history(self, command: Optional[str] = None) -> List[ZenCommandResult]:
        """Get command execution history"""
        if command:
            return [r for r in self._command_history if r.command == command]
        return self._command_history.copy()
    
    def get_command_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for command execution"""
        stats = {}
        
        for result in self._command_history:
            if result.command not in stats:
                stats[result.command] = {
                    'total_executions': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0
                }
            
            cmd_stats = stats[result.command]
            cmd_stats['total_executions'] += 1
            cmd_stats['total_time'] += result.execution_time
            
            if result.success:
                cmd_stats['successful'] += 1
            else:
                cmd_stats['failed'] += 1
            
            cmd_stats['avg_time'] = cmd_stats['total_time'] / cmd_stats['total_executions']
        
        return stats