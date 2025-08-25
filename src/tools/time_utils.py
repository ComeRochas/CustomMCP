from datetime import datetime, timezone
import asyncio

"""Time utility tools."""

class TimeTools:
    """Time-related utilities for the MCP server."""
    
    async def get_current_time(self) -> str:
        """Get current UTC time in ISO format."""
        # Simulate async operation
        await asyncio.sleep(0.001)
        return datetime.now(timezone.utc).isoformat()
