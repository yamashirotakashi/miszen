"""
MIS (Memory Integration System) connector for miszen.
Provides integration with MIS Knowledge Graph and Memory Bank.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import httpx
from datetime import datetime

from ..core.config import config


logger = logging.getLogger(__name__)


@dataclass
class MISEntity:
    """MIS entity representation"""
    name: str
    entity_type: str
    observations: List[str]
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MIS API format"""
        data = {
            'name': self.name,
            'entityType': self.entity_type,
            'observations': self.observations
        }
        if self.tags:
            data['tags'] = self.tags
        return data


@dataclass
class MISRelation:
    """MIS relation representation"""
    from_entity: str
    to_entity: str
    relation_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MIS API format"""
        return {
            'from': self.from_entity,
            'to': self.to_entity,
            'relationType': self.relation_type
        }


class MISConnector:
    """Connector for MIS API"""
    
    def __init__(self):
        self.api_base_url = config.mis.api_base_url
        self.kg_endpoint = config.mis.knowledge_graph_endpoint
        self.mb_endpoint = config.mis.memory_bank_endpoint
        self.client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={
                'Authorization': f'Bearer {config.mis.api_token}',
                'Content-Type': 'application/json'
            } if hasattr(config.mis, 'api_token') else {'Content-Type': 'application/json'},
            timeout=30.0
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    # Knowledge Graph operations
    
    async def create_entities(self, entities: List[MISEntity]) -> Dict[str, Any]:
        """Create entities in Knowledge Graph"""
        try:
            data = {
                'entities': [e.to_dict() for e in entities]
            }
            
            response = await self.client.post(
                f"{self.kg_endpoint}/entities",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created {len(entities)} entities in Knowledge Graph")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to create entities: {e}")
            raise
    
    async def create_relations(self, relations: List[MISRelation]) -> Dict[str, Any]:
        """Create relations in Knowledge Graph"""
        try:
            data = {
                'relations': [r.to_dict() for r in relations]
            }
            
            response = await self.client.post(
                f"{self.kg_endpoint}/relations",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created {len(relations)} relations in Knowledge Graph")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to create relations: {e}")
            raise
    
    async def search_knowledge(self, query: str, search_mode: str = 'exact') -> Dict[str, Any]:
        """Search Knowledge Graph"""
        try:
            params = {
                'query': query,
                'searchMode': search_mode
            }
            
            response = await self.client.get(
                f"{self.kg_endpoint}/search",
                params=params
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to search knowledge: {e}")
            raise
    
    async def add_observations(self, entity_name: str, observations: List[str]) -> Dict[str, Any]:
        """Add observations to existing entity"""
        try:
            data = {
                'observations': [{
                    'entityName': entity_name,
                    'observations': observations
                }]
            }
            
            response = await self.client.post(
                f"{self.kg_endpoint}/observations",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Added {len(observations)} observations to {entity_name}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to add observations: {e}")
            raise
    
    # Memory Bank operations
    
    async def create_memory(self, key: str, value: Any, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create memory in Memory Bank"""
        try:
            data = {
                'key': key,
                'value': value,
                'tags': tags or [],
                'timestamp': datetime.now().isoformat()
            }
            
            response = await self.client.post(
                f"{self.mb_endpoint}/memories",
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created memory: {key}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to create memory: {e}")
            raise
    
    async def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get memory from Memory Bank"""
        try:
            response = await self.client.get(
                f"{self.mb_endpoint}/memories/{key}"
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get memory: {e}")
            raise
    
    async def search_memories(self, query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search memories in Memory Bank"""
        try:
            params = {
                'query': query
            }
            if tags:
                params['tags'] = ','.join(tags)
            
            response = await self.client.get(
                f"{self.mb_endpoint}/search",
                params=params
            )
            response.raise_for_status()
            
            return response.json().get('memories', [])
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to search memories: {e}")
            raise
    
    # Integration helpers
    
    async def record_command_execution(self, command: str, params: Dict[str, Any], 
                                     result: Any, success: bool, execution_time: float):
        """Record zen-MCP command execution in MIS"""
        # Create entity for the command execution
        entity = MISEntity(
            name=f"zen_command_{command}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            entity_type='command_execution',
            observations=[
                f"Command: {command}",
                f"Success: {success}",
                f"Execution time: {execution_time:.2f}s",
                f"Parameters: {params}",
                f"Result preview: {str(result)[:200]}..." if result else "No result"
            ],
            tags=[command, 'zen-mcp', 'success' if success else 'failure']
        )
        
        await self.create_entities([entity])
        
        # Also save to Memory Bank for quick access
        memory_key = f"zen_command_last_{command}"
        await self.create_memory(
            memory_key,
            {
                'command': command,
                'params': params,
                'result': result if success else None,
                'error': str(result) if not success else None,
                'success': success,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            },
            tags=[command, 'zen-mcp', 'last_execution']
        )
    
    async def get_command_context(self, command: str) -> Optional[Dict[str, Any]]:
        """Get context for a command from previous executions"""
        # Try to get last execution from Memory Bank
        last_execution = await self.get_memory(f"zen_command_last_{command}")
        
        # Search for related entities in Knowledge Graph
        search_result = await self.search_knowledge(f"zen_command_{command}", search_mode='fuzzy')
        
        context = {
            'last_execution': last_execution,
            'related_executions': search_result.get('entities', [])[:5],  # Last 5 executions
            'command': command
        }
        
        return context
    
    async def record_event_processing(self, event_id: str, event_type: str, 
                                    triggered_commands: List[str], success: bool):
        """Record event processing in MIS"""
        # Create entity for the event processing
        entity = MISEntity(
            name=f"event_processing_{event_id}",
            entity_type='event_processing',
            observations=[
                f"Event type: {event_type}",
                f"Event ID: {event_id}",
                f"Triggered commands: {', '.join(triggered_commands)}",
                f"Success: {success}",
                f"Timestamp: {datetime.now().isoformat()}"
            ],
            tags=[event_type, 'event', 'success' if success else 'failure']
        )
        
        await self.create_entities([entity])
        
        # Create relations to triggered commands
        if triggered_commands:
            relations = []
            for command in triggered_commands:
                # Search for the command entity
                search_result = await self.search_knowledge(f"zen_command_{command}", search_mode='fuzzy')
                if search_result.get('entities'):
                    latest_command = search_result['entities'][0]['name']
                    relations.append(MISRelation(
                        from_entity=f"event_processing_{event_id}",
                        to_entity=latest_command,
                        relation_type='triggered'
                    ))
            
            if relations:
                await self.create_relations(relations)