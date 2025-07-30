from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
import logging
import os
from config import config
from tools import CalculatorTools, WeatherTools, TimeTools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    server = FastMCP(
        name="CustomMCP-Server",
        description="Advanced MCP server with weather, calculator, and utility tools",
        host=config.HOST,
        port=config.PORT,
        stateless_http=True,
    )
    
    # Initialize tool handlers
    calc_tools = CalculatorTools()
    weather_tools = WeatherTools()
    time_tools = TimeTools()
    
    # Register calculator tools
    @server.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers together."""
        return calc_tools.add(a, b)
    
    @server.tool()
    def subtract(a: int, b: int) -> int:
        """Subtract second number from first."""
        return calc_tools.subtract(a, b)
    
    @server.tool()
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return calc_tools.multiply(a, b)
    
    # Register weather tools
    @server.tool()
    async def get_forecast(latitude: float, longitude: float) -> str:
        """Get weather forecast for a location.
        
        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
        """
        try:
            return await weather_tools.get_forecast(latitude, longitude)
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return f"Error retrieving forecast: {str(e)}"
    
    @server.tool()
    async def get_alerts(state: str) -> str:
        """Get weather alerts for a US state.
        
        Args:
            state: Two-letter US state code (e.g., CA, NY)
        """
        try:
            return await weather_tools.get_alerts(state.upper())
        except Exception as e:
            logger.error(f"Alerts error: {e}")
            return f"Error retrieving alerts: {str(e)}"
    
    # Register utility tools
    @server.tool()
    async def get_time(ctx: Context) -> str:
        """Returns the current server date and time in UTC."""
        return await time_tools.get_current_time()
    
    return server

def main():
    """Main server entry point."""
    try:
        config.validate()
        server = create_server()
        
        logger.info(f"Starting CustomMCP server on {config.HOST}:{config.PORT}")
        logger.info(f"Transport mode: {config.TRANSPORT}")
        
        server.run(transport=config.TRANSPORT)
        
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        raise

if __name__ == "__main__":
    main()