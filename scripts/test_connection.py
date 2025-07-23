#!/usr/bin/env python3
"""
Test script for MCP connection and basic zen-MCP commands.
This is a real connection test, not a mock.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import config
from src.adapters.zen_mcp_adapter import ZenMCPAdapter
from src.events.event_types import create_file_event, create_error_event
from src.events.event_handler import EventHandler


async def test_connection():
    """Test basic MCP connection"""
    print("Testing MCP connection...")
    print(f"Connecting to {config.mcp.host}:{config.mcp.port}")
    
    adapter = ZenMCPAdapter()
    
    try:
        # Test connection
        connected = await adapter.connect()
        if connected:
            print("✓ Successfully connected to MCP server")
        else:
            print("✗ Failed to connect to MCP server")
            return False
        
        # Test version command
        print("\nTesting version command...")
        result = await adapter.version()
        if result.success:
            print(f"✓ Version command successful: {result.result}")
        else:
            print(f"✗ Version command failed: {result.error}")
        
        # Test listmodels command
        print("\nTesting listmodels command...")
        result = await adapter.listmodels()
        if result.success:
            print("✓ Listmodels command successful")
            print(f"  Available models: {len(result.result.get('models', []))}")
        else:
            print(f"✗ Listmodels command failed: {result.error}")
        
        # Test chat command
        print("\nTesting chat command...")
        result = await adapter.chat("Hello, this is a test message from miszen project")
        if result.success:
            print("✓ Chat command successful")
            print(f"  Response preview: {str(result.result)[:100]}...")
        else:
            print(f"✗ Chat command failed: {result.error}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False
    
    finally:
        await adapter.disconnect()
        print("\nDisconnected from MCP server")


async def test_event_handling():
    """Test event handling system"""
    print("\n" + "="*50)
    print("Testing Event Handling System")
    print("="*50)
    
    adapter = ZenMCPAdapter()
    handler = EventHandler(adapter)
    
    try:
        # Connect adapter
        connected = await adapter.connect()
        if not connected:
            print("✗ Failed to connect adapter")
            return False
        
        # Start event handler
        await handler.start()
        print("✓ Event handler started")
        
        # Test file creation event
        print("\nTesting file_created event...")
        file_event = create_file_event(
            "file_created",
            "/test/example.py",
            lines=50,
            author="test_user"
        )
        
        await handler.handle_event(file_event)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check processing stats
        stats = handler.get_processing_stats()
        print(f"  Queue size: {stats['queue_size']}")
        print(f"  Processed events: {stats['processed_events']}")
        
        # Test error event
        print("\nTesting error_detected event...")
        error_event = create_error_event(
            "Test error message",
            severity="error",
            file="/test/error.py",
            line=42
        )
        
        await handler.handle_event(error_event)
        
        # Wait for processing
        await asyncio.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"✗ Event handling test failed: {e}")
        return False
    
    finally:
        await handler.stop()
        await adapter.disconnect()
        print("\nCleaned up resources")


async def main():
    """Main test function"""
    print("MIS-Zenmcp Integration Test Suite")
    print("="*50)
    
    # Check environment
    print("Environment Configuration:")
    print(f"  MCP Host: {config.mcp.host}")
    print(f"  MCP Port: {config.mcp.port}")
    print(f"  MIS API URL: {config.mis.api_base_url}")
    print(f"  Debug Mode: {config.debug}")
    print(f"  Log Level: {config.log_level}")
    
    # Run connection test
    connection_ok = await test_connection()
    
    if not connection_ok:
        print("\n✗ Connection test failed. Skipping further tests.")
        return
    
    # Run event handling test
    await test_event_handling()
    
    print("\n" + "="*50)
    print("Test suite completed")


if __name__ == "__main__":
    asyncio.run(main())