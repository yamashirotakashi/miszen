"""
Chat command integration for MIS-zen-MCP.
Provides context-aware chat functionality with memory integration.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..adapters.zen_mcp_adapter import ZenMCPAdapter, ZenCommandResult
from ..adapters.mis_connector import MISConnector, MISEntity
from ..events.event_types import MISEvent


logger = logging.getLogger(__name__)


class ChatIntegration:
    """Integration layer for zen-MCP chat command"""
    
    def __init__(self, zen_adapter: ZenMCPAdapter, mis_connector: MISConnector):
        self.zen_adapter = zen_adapter
        self.mis_connector = mis_connector
        self.conversation_history: List[Dict[str, Any]] = []
        self.current_session_id: Optional[str] = None
    
    async def start_session(self, session_id: Optional[str] = None) -> str:
        """Start a new chat session"""
        if session_id is None:
            import uuid
            session_id = f"chat_session_{uuid.uuid4()}"
        
        self.current_session_id = session_id
        self.conversation_history = []
        
        # Create session entity in Knowledge Graph
        entity = MISEntity(
            name=session_id,
            entity_type='chat_session',
            observations=[
                f"Session started at {datetime.now().isoformat()}",
                "Type: MIS-zen-MCP integrated chat",
                "Status: active"
            ],
            tags=['chat', 'session', 'active']
        )
        
        await self.mis_connector.create_entities([entity])
        logger.info(f"Started chat session: {session_id}")
        
        return session_id
    
    async def chat_with_context(self, prompt: str, event: Optional[MISEvent] = None, 
                               use_memory: bool = True, **kwargs) -> ZenCommandResult:
        """Execute chat command with MIS context"""
        # Build context from various sources
        context = await self._build_context(prompt, event, use_memory)
        
        # Prepare enhanced prompt with context
        enhanced_prompt = self._enhance_prompt(prompt, context)
        
        # Get command-specific parameters from kwargs
        params = {
            'prompt': enhanced_prompt,
            'continuation_id': kwargs.get('continuation_id'),
            'temperature': kwargs.get('temperature', 0.7),
            'model': kwargs.get('model'),
            'use_websearch': kwargs.get('use_websearch', True)
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Execute chat command
        result = await self.zen_adapter.chat(**params)
        
        # Record conversation turn
        await self._record_conversation_turn(prompt, result, context)
        
        # Update session if active
        if self.current_session_id:
            await self._update_session(prompt, result)
        
        return result
    
    async def _build_context(self, prompt: str, event: Optional[MISEvent], 
                           use_memory: bool) -> Dict[str, Any]:
        """Build context from various sources"""
        context = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.current_session_id,
            'conversation_history': self.conversation_history[-5:]  # Last 5 turns
        }
        
        # Add event context if provided
        if event:
            context['triggering_event'] = {
                'type': event.event_type,
                'data': event.data,
                'metadata': event.metadata.to_dict()
            }
        
        # Add memory context if enabled
        if use_memory:
            # Get previous chat context
            chat_context = await self.mis_connector.get_command_context('chat')
            if chat_context:
                context['previous_executions'] = chat_context
            
            # Search for relevant memories based on prompt
            memories = await self._search_relevant_memories(prompt)
            if memories:
                context['relevant_memories'] = memories
            
            # Search Knowledge Graph for related information
            kg_results = await self._search_knowledge_graph(prompt)
            if kg_results:
                context['knowledge_graph'] = kg_results
        
        return context
    
    async def _search_relevant_memories(self, prompt: str) -> List[Dict[str, Any]]:
        """Search for relevant memories based on prompt"""
        # Extract key terms from prompt (simple implementation)
        keywords = [word for word in prompt.lower().split() 
                   if len(word) > 4 and word not in ['about', 'please', 'could', 'would']]
        
        memories = []
        
        # Search memories for each keyword
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            try:
                results = await self.mis_connector.search_memories(keyword)
                memories.extend(results[:2])  # Take top 2 results per keyword
            except Exception as e:
                logger.warning(f"Failed to search memories for '{keyword}': {e}")
        
        # Remove duplicates
        seen = set()
        unique_memories = []
        for memory in memories:
            key = memory.get('key')
            if key and key not in seen:
                seen.add(key)
                unique_memories.append(memory)
        
        return unique_memories[:5]  # Return top 5 unique memories
    
    async def _search_knowledge_graph(self, prompt: str) -> Dict[str, Any]:
        """Search Knowledge Graph for relevant information"""
        try:
            # Use fuzzy search for better results
            results = await self.mis_connector.search_knowledge(prompt, search_mode='fuzzy')
            
            # Filter and format results
            entities = results.get('entities', [])[:3]  # Top 3 entities
            relations = results.get('relations', [])[:5]  # Top 5 relations
            
            return {
                'entities': entities,
                'relations': relations,
                'total_found': len(results.get('entities', []))
            }
            
        except Exception as e:
            logger.warning(f"Failed to search Knowledge Graph: {e}")
            return {}
    
    def _enhance_prompt(self, original_prompt: str, context: Dict[str, Any]) -> str:
        """Enhance prompt with context information"""
        enhanced_parts = [original_prompt]
        
        # Add event context if present
        if 'triggering_event' in context:
            event_info = context['triggering_event']
            enhanced_parts.append(
                f"\n\n[Event Context: {event_info['type']} event with data: {event_info['data']}]"
            )
        
        # Add conversation history if present
        if context.get('conversation_history'):
            history_text = "\n\n[Recent Conversation History:]"
            for turn in context['conversation_history']:
                history_text += f"\nUser: {turn['user_prompt'][:100]}..."
                history_text += f"\nAssistant: {turn['assistant_response'][:100]}..."
            enhanced_parts.append(history_text)
        
        # Add relevant memories if present
        if context.get('relevant_memories'):
            memory_text = "\n\n[Relevant Context from Memory:]"
            for memory in context['relevant_memories'][:3]:
                memory_text += f"\n- {memory.get('key', 'Unknown')}: {str(memory.get('value', ''))[:100]}..."
            enhanced_parts.append(memory_text)
        
        # Add Knowledge Graph context if present
        if context.get('knowledge_graph', {}).get('entities'):
            kg_text = "\n\n[Related Knowledge:]"
            for entity in context['knowledge_graph']['entities'][:2]:
                kg_text += f"\n- {entity['name']} ({entity['entityType']}): {entity['observations'][0]}"
            enhanced_parts.append(kg_text)
        
        return "\n".join(enhanced_parts)
    
    async def _record_conversation_turn(self, prompt: str, result: ZenCommandResult, 
                                      context: Dict[str, Any]):
        """Record conversation turn in memory"""
        turn = {
            'user_prompt': prompt,
            'assistant_response': result.result if result.success else f"Error: {result.error}",
            'timestamp': datetime.now().isoformat(),
            'success': result.success,
            'execution_time': result.execution_time,
            'context_used': bool(context.get('relevant_memories') or context.get('knowledge_graph'))
        }
        
        self.conversation_history.append(turn)
        
        # Save to Memory Bank
        if self.current_session_id:
            memory_key = f"{self.current_session_id}_turn_{len(self.conversation_history)}"
            await self.mis_connector.create_memory(
                memory_key,
                turn,
                tags=['chat', 'conversation', self.current_session_id]
            )
    
    async def _update_session(self, prompt: str, result: ZenCommandResult):
        """Update session entity with new information"""
        if not self.current_session_id:
            return
        
        observations = [
            f"Turn {len(self.conversation_history)}: User asked about '{prompt[:50]}...'",
            f"Response success: {result.success}",
            f"Execution time: {result.execution_time:.2f}s"
        ]
        
        await self.mis_connector.add_observations(self.current_session_id, observations)
    
    async def end_session(self) -> Optional[str]:
        """End current chat session"""
        if not self.current_session_id:
            return None
        
        # Update session status
        observations = [
            f"Session ended at {datetime.now().isoformat()}",
            f"Total turns: {len(self.conversation_history)}",
            "Status: completed"
        ]
        
        await self.mis_connector.add_observations(self.current_session_id, observations)
        
        # Save conversation summary
        if self.conversation_history:
            summary = {
                'session_id': self.current_session_id,
                'start_time': self.conversation_history[0]['timestamp'],
                'end_time': self.conversation_history[-1]['timestamp'],
                'total_turns': len(self.conversation_history),
                'topics_discussed': self._extract_topics(),
                'average_response_time': sum(t['execution_time'] for t in self.conversation_history) / len(self.conversation_history)
            }
            
            await self.mis_connector.create_memory(
                f"{self.current_session_id}_summary",
                summary,
                tags=['chat', 'session_summary', 'completed']
            )
        
        session_id = self.current_session_id
        self.current_session_id = None
        self.conversation_history = []
        
        logger.info(f"Ended chat session: {session_id}")
        return session_id
    
    def _extract_topics(self) -> List[str]:
        """Extract main topics from conversation (simple implementation)"""
        # This is a placeholder - in real implementation, could use NLP
        topics = []
        
        # Extract from user prompts
        all_text = " ".join(turn['user_prompt'] for turn in self.conversation_history)
        
        # Simple keyword extraction (can be improved)
        common_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'of', 'for', 'in', 'to', 'with'}
        words = all_text.lower().split()
        word_count = {}
        
        for word in words:
            if len(word) > 4 and word not in common_words:
                word_count[word] = word_count.get(word, 0) + 1
        
        # Get top 5 most frequent words as topics
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        topics = [word for word, count in sorted_words[:5] if count > 1]
        
        return topics