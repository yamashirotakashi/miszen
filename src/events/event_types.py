"""
MIS event type definitions and structures.
Provides abstraction for all event types without hardcoding.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class EventPriority(Enum):
    """Event priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventCategory(Enum):
    """Event categories for grouping"""
    FILE_SYSTEM = "file_system"
    CODE_CHANGE = "code_change"
    ERROR = "error"
    TEST = "test"
    SECURITY = "security"
    WORKFLOW = "workflow"
    SYSTEM = "system"


@dataclass
class EventMetadata:
    """Metadata for events"""
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.MEDIUM
    category: EventCategory = EventCategory.SYSTEM
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'category': self.category.value,
            'tags': self.tags,
            'correlation_id': self.correlation_id,
            'parent_event_id': self.parent_event_id
        }


@dataclass
class MISEvent:
    """Base class for all MIS events"""
    event_type: str
    data: Dict[str, Any]
    metadata: EventMetadata
    event_id: Optional[str] = None
    
    def __post_init__(self):
        if self.event_id is None:
            import uuid
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'data': self.data,
            'metadata': self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MISEvent':
        """Create from dictionary"""
        metadata_dict = data.get('metadata', {})
        metadata = EventMetadata(
            source=metadata_dict.get('source', 'unknown'),
            timestamp=datetime.fromisoformat(metadata_dict.get('timestamp', datetime.now().isoformat())),
            priority=EventPriority(metadata_dict.get('priority', 'medium')),
            category=EventCategory(metadata_dict.get('category', 'system')),
            tags=metadata_dict.get('tags', []),
            correlation_id=metadata_dict.get('correlation_id'),
            parent_event_id=metadata_dict.get('parent_event_id')
        )
        
        return cls(
            event_id=data.get('event_id'),
            event_type=data.get('event_type', 'unknown'),
            data=data.get('data', {}),
            metadata=metadata
        )
    
    def matches_conditions(self, conditions: Dict[str, Any]) -> bool:
        """Check if event matches given conditions"""
        for key, expected_value in conditions.items():
            if key == 'extensions':
                # Check file extensions
                file_path = self.data.get('file_path', '')
                if not any(file_path.endswith(ext) for ext in expected_value):
                    return False
            elif key == 'severity':
                # Check severity levels
                if self.data.get('severity') not in expected_value:
                    return False
            elif key == 'min_lines':
                # Check minimum lines changed
                lines_changed = self.data.get('lines_changed', 0)
                if lines_changed < expected_value:
                    return False
            elif key in self.data:
                # Direct field comparison
                if self.data[key] != expected_value:
                    return False
        
        return True


# Predefined event factories for common event types

def create_file_event(event_type: str, file_path: str, **kwargs) -> MISEvent:
    """Create a file system event"""
    return MISEvent(
        event_type=event_type,
        data={
            'file_path': file_path,
            'file_name': file_path.split('/')[-1],
            'extension': '.' + file_path.split('.')[-1] if '.' in file_path else '',
            **kwargs
        },
        metadata=EventMetadata(
            source='file_system',
            category=EventCategory.FILE_SYSTEM,
            tags=['file', event_type]
        )
    )


def create_error_event(error_message: str, severity: str = 'error', **kwargs) -> MISEvent:
    """Create an error event"""
    priority_map = {
        'warning': EventPriority.LOW,
        'error': EventPriority.HIGH,
        'critical': EventPriority.CRITICAL
    }
    
    return MISEvent(
        event_type='error_detected',
        data={
            'error_message': error_message,
            'severity': severity,
            **kwargs
        },
        metadata=EventMetadata(
            source='error_handler',
            category=EventCategory.ERROR,
            priority=priority_map.get(severity, EventPriority.MEDIUM),
            tags=['error', severity]
        )
    )


def create_code_change_event(file_path: str, lines_changed: int, **kwargs) -> MISEvent:
    """Create a code change event"""
    return MISEvent(
        event_type='code_changed',
        data={
            'file_path': file_path,
            'lines_changed': lines_changed,
            'change_type': kwargs.get('change_type', 'modification'),
            **kwargs
        },
        metadata=EventMetadata(
            source='code_monitor',
            category=EventCategory.CODE_CHANGE,
            tags=['code', 'change']
        )
    )


def create_test_event(test_name: str, status: str, **kwargs) -> MISEvent:
    """Create a test event"""
    event_type = 'test_passed' if status == 'passed' else 'test_failed'
    
    return MISEvent(
        event_type=event_type,
        data={
            'test_name': test_name,
            'status': status,
            **kwargs
        },
        metadata=EventMetadata(
            source='test_runner',
            category=EventCategory.TEST,
            priority=EventPriority.HIGH if status == 'failed' else EventPriority.LOW,
            tags=['test', status]
        )
    )


def create_security_event(alert_type: str, description: str, **kwargs) -> MISEvent:
    """Create a security event"""
    return MISEvent(
        event_type='security_alert',
        data={
            'alert_type': alert_type,
            'description': description,
            **kwargs
        },
        metadata=EventMetadata(
            source='security_monitor',
            category=EventCategory.SECURITY,
            priority=EventPriority.CRITICAL,
            tags=['security', alert_type]
        )
    )