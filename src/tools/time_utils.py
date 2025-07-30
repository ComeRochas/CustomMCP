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
    
    async def get_timestamp(self) -> int:
        """Get current Unix timestamp."""
        await asyncio.sleep(0.001)
        return int(datetime.now(timezone.utc).timestamp())
    
    def format_time(self, timestamp: int, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format a Unix timestamp to readable string."""
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime(format_str)