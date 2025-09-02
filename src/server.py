from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
import logging
import os
from config import config
from tools import CalculatorTools, WeatherTools, TimeTools, LocationTools, WebSearch
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    location_tools = LocationTools()
    web_tools = WebSearch(brave_api_key=os.getenv("BRAVE_API_KEY"), logger=logger)
    
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
        """Get weather forecast for a location in the US.

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
    
    
    @server.tool()
    async def get_time(ctx: Context) -> str:
        """Get current UTC time in ISO format."""
        return await time_tools.get_current_time()
    
    
    @server.tool()
    async def get_location() -> dict:
        """Get current location using IP geolocation.
        
        Returns location information including coordinates, city, country, and timezone.
        """
        try:
            return await location_tools.get_location()
        except Exception as e:
            logger.error(f"Location error: {e}")
            return {
                'status': 'error',
                'message': f"Error retrieving location: {str(e)}"
            }
    
    @server.tool()
    async def get_location_by_ip(ip_address: str) -> dict:
        """Get location information for a specific IP address.
        
        Args:
            ip_address: The IP address to geolocate
            
        Returns location information for the given IP address.
        """
        try:
            return await location_tools.get_location_by_ip(ip_address)
        except Exception as e:
            logger.error(f"IP location error: {e}")
            return {
                'status': 'error',
                'message': f"Error retrieving location for IP {ip_address}: {str(e)}"
            }
    
    
    @server.tool()
    async def brave_search(keywords: str, max_results: int = 5, country: Optional[str] = "us") -> List[Dict[str, Any]]:
        """Search the web using BraveSearch API.
        
        Args:
            keywords: Search query
            max_results: Maximum number of results to return (use less than 5 unless you really think more is needed).
            country: 2-letter country code (e.g., "us", "fr", "sg")

        Returns a list of search results with title, URL, and snippet.
        """
        try:
            return await web_tools.brave_search(keywords, max_results, country)
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return [{
                'error': True,
                'message': f"Web search failed: {str(e)}"
            }]
    
    
    @server.tool()
    async def fetch_url_content(url: str, max_length: int = 5000, mode: str = "readable") -> dict:
        """Fetch and extract text content from a URL.
        
        Args:
            url: URL to fetch content from
            max_length: Maximum length of text content to return (default: 5000)
            mode: "readable" returns extracted article text ; "raw" returns HTML text
        """
        try:
            return await web_tools.fetch_url_content(url, max_length, mode)
        except Exception as e:
            logger.error(f"URL fetch error: {e}")
            return {
                'url': url,
                'status': 'error',
                'message': f"Failed to fetch URL: {str(e)}"
            }

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