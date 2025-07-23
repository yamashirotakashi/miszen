"""
Event handler for processing MIS events and triggering zen-MCP commands.
Implements the event-driven architecture without hardcoding.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass
from datetime import datetime

from ..core.config import config
from ..adapters.zen_mcp_adapter import ZenMCPAdapter, ZenCommandResult
from .event_types import MISEvent, EventPriority


logger = logging.getLogger(__name__)


@dataclass
class EventProcessingResult:
    """Result of event processing"""
    event: MISEvent
    triggered_commands: List[str]
    command_results: List[ZenCommandResult]
    success: bool
    processing_time: float
    error: Optional[str] = None


class EventHandler:
    """Handles MIS events and triggers appropriate zen-MCP commands"""
    
    def __init__(self, zen_adapter: ZenMCPAdapter):
        self.zen_adapter = zen_adapter
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.event_filters: List[Callable[[MISEvent], bool]] = []
        self.pre_processors: List[Callable[[MISEvent], MISEvent]] = []
        self.post_processors: List[Callable[[EventProcessingResult], None]] = []
        self._running = False
        self._processed_events: Set[str] = set()
        
    def add_filter(self, filter_func: Callable[[MISEvent], bool]):
        """Add an event filter"""
        self.event_filters.append(filter_func)
    
    def add_pre_processor(self, processor: Callable[[MISEvent], MISEvent]):
        """Add a pre-processor for events"""
        self.pre_processors.append(processor)
    
    def add_post_processor(self, processor: Callable[[EventProcessingResult], None]):
        """Add a post-processor for results"""
        self.post_processors.append(processor)
    
    async def start(self):
        """Start the event handler"""
        if not self._running:
            self._running = True
            self.processing_task = asyncio.create_task(self._process_events())
            logger.info("Event handler started")
    
    async def stop(self):
        """Stop the event handler"""
        self._running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Event handler stopped")
    
    async def handle_event(self, event: MISEvent) -> Optional[EventProcessingResult]:
        """Handle a single event"""
        # Check if event was already processed (deduplication)
        if event.event_id in self._processed_events:
            logger.debug(f"Skipping duplicate event: {event.event_id}")
            return None
        
        # Apply filters
        for filter_func in self.event_filters:
            if not filter_func(event):
                logger.debug(f"Event {event.event_id} filtered out")
                return None
        
        # Add to processing queue
        await self.event_queue.put(event)
        return None
    
    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Process the event
                result = await self._process_single_event(event)
                
                # Mark as processed
                self._processed_events.add(event.event_id)
                
                # Apply post-processors
                for processor in self.post_processors:
                    try:
                        processor(result)
                    except Exception as e:
                        logger.error(f"Post-processor error: {e}")
                
                # Clean up old processed events (keep last 1000)
                if len(self._processed_events) > 1000:
                    self._processed_events = set(
                        list(self._processed_events)[-500:]
                    )
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event processing error: {e}", exc_info=True)
    
    async def _process_single_event(self, event: MISEvent) -> EventProcessingResult:
        """Process a single event"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Apply pre-processors
            for processor in self.pre_processors:
                event = processor(event)
            
            # Get commands for this event type
            commands = config.get_event_commands(event.event_type)
            conditions = config.get_event_conditions(event.event_type)
            
            # Check if event matches conditions
            if not event.matches_conditions(conditions):
                logger.debug(f"Event {event.event_id} doesn't match conditions")
                return EventProcessingResult(
                    event=event,
                    triggered_commands=[],
                    command_results=[],
                    success=True,
                    processing_time=asyncio.get_event_loop().time() - start_time
                )
            
            # Execute commands
            command_results = []
            for command in commands:
                try:
                    # Prepare command parameters based on event data
                    params = self._prepare_command_params(command, event)
                    
                    # Execute command
                    result = await self.zen_adapter.execute_command(command, params)
                    command_results.append(result)
                    
                    logger.info(f"Executed {command} for event {event.event_type}")
                    
                except Exception as e:
                    logger.error(f"Failed to execute {command}: {e}")
                    # Create error result
                    command_results.append(ZenCommandResult(
                        command=command,
                        success=False,
                        result=None,
                        error=str(e)
                    ))
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return EventProcessingResult(
                event=event,
                triggered_commands=commands,
                command_results=command_results,
                success=all(r.success for r in command_results),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Event processing failed: {e}", exc_info=True)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return EventProcessingResult(
                event=event,
                triggered_commands=[],
                command_results=[],
                success=False,
                processing_time=processing_time,
                error=str(e)
            )
    
    def _prepare_command_params(self, command: str, event: MISEvent) -> Dict[str, Any]:
        """Prepare parameters for a zen-MCP command based on event data"""
        params = {}
        
        # Common parameters
        if command in ['analyze', 'debug', 'codereview', 'refactor', 'testgen', 'docgen']:
            # These commands need a 'step' parameter
            params['step'] = self._generate_step_description(command, event)
            
            # Add file information if available
            if 'file_path' in event.data:
                params['relevant_files'] = [event.data['file_path']]
        
        elif command == 'chat':
            # Chat needs a prompt
            params['prompt'] = self._generate_chat_prompt(event)
        
        elif command == 'thinkdeep':
            # Thinkdeep needs deep analysis context
            params['step'] = self._generate_analysis_context(event)
            params['thinking_mode'] = 'high'
        
        elif command == 'tracer':
            # Tracer needs target description
            params['target_description'] = self._generate_trace_target(event)
        
        elif command == 'secaudit':
            # Security audit needs security context
            params['step'] = self._generate_security_context(event)
            params['audit_focus'] = 'comprehensive'
        
        # Add event context to all commands
        params['context'] = {
            'event_type': event.event_type,
            'event_data': event.data,
            'event_metadata': event.metadata.to_dict()
        }
        
        return params
    
    def _generate_step_description(self, command: str, event: MISEvent) -> str:
        """Generate step description for workflow commands"""
        descriptions = {
            'analyze': f"Analyze {event.event_type} event: {event.data}",
            'debug': f"Debug issue from {event.event_type}: {event.data.get('error_message', 'Unknown error')}",
            'codereview': f"Review code changes in {event.data.get('file_path', 'unknown file')}",
            'refactor': f"Refactor code in {event.data.get('file_path', 'unknown file')}",
            'testgen': f"Generate tests for {event.data.get('file_path', 'unknown file')}",
            'docgen': f"Generate documentation for {event.data.get('file_path', 'unknown file')}"
        }
        return descriptions.get(command, f"Process {event.event_type} event")
    
    def _generate_chat_prompt(self, event: MISEvent) -> str:
        """Generate chat prompt based on event"""
        if event.event_type == 'error_detected':
            return f"Help me understand this error: {event.data.get('error_message', 'Unknown error')}"
        elif event.event_type == 'file_created':
            return f"What should I consider for the new file: {event.data.get('file_path', 'unknown file')}?"
        else:
            return f"Process event {event.event_type} with data: {event.data}"
    
    def _generate_analysis_context(self, event: MISEvent) -> str:
        """Generate analysis context for thinkdeep"""
        return f"Deep analysis required for {event.event_type} event. Context: {event.data}. Priority: {event.metadata.priority.value}"
    
    def _generate_trace_target(self, event: MISEvent) -> str:
        """Generate trace target for tracer command"""
        if 'error_message' in event.data and 'stack_trace' in event.data:
            return f"Trace error: {event.data['error_message']} from stack trace"
        elif 'file_path' in event.data:
            return f"Trace execution flow in {event.data['file_path']}"
        else:
            return f"Trace event flow for {event.event_type}"
    
    def _generate_security_context(self, event: MISEvent) -> str:
        """Generate security context for secaudit"""
        return f"Security audit triggered by {event.event_type}. Alert: {event.data.get('description', 'Security concern detected')}"
    
    def get_queue_size(self) -> int:
        """Get current event queue size"""
        return self.event_queue.qsize()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        return {
            'queue_size': self.get_queue_size(),
            'processed_events': len(self._processed_events),
            'is_running': self._running,
            'filters_count': len(self.event_filters),
            'pre_processors_count': len(self.pre_processors),
            'post_processors_count': len(self.post_processors)
        }