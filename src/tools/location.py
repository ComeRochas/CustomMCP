"""Location tools implementation."""

import aiohttp
import json
from typing import Dict, Any, Optional

class LocationTools:
    """Location services for the MCP server."""
    
    async def get_location(self) -> Dict[str, Any]:
        """Get current location using IP geolocation.
        
        Returns:
            Dictionary containing location information including:
            - ip: IP address
            - latitude: Latitude coordinate
            - longitude: Longitude coordinate
            - city: City name
            - country: Country name
            - timezone: Timezone
        """
        try:
            # Use a free IP geolocation service
            async with aiohttp.ClientSession() as session:
                async with session.get('http://ip-api.com/json/?fields=status,message,country,city,lat,lon,timezone,query') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'success':
                            return {
                                'ip': data.get('query'),
                                'latitude': data.get('lat'),
                                'longitude': data.get('lon'),
                                'city': data.get('city'),
                                'country': data.get('country'),
                                'timezone': data.get('timezone'),
                                'status': 'success'
                            }
                        else:
                            return {
                                'status': 'error',
                                'message': data.get('message', 'Unknown error')
                            }
                    else:
                        return {
                            'status': 'error',
                            'message': f'HTTP error: {response.status}'
                        }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get location: {str(e)}'
            }
    
    async def get_location_by_ip(self, ip_address: str) -> Dict[str, Any]:
        """Get location information for a specific IP address.
        
        Args:
            ip_address: The IP address to geolocate
            
        Returns:
            Dictionary containing location information for the given IP
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f'http://ip-api.com/json/{ip_address}?fields=status,message,country,city,lat,lon,timezone,query'
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'success':
                            return {
                                'ip': data.get('query'),
                                'latitude': data.get('lat'),
                                'longitude': data.get('lon'),
                                'city': data.get('city'),
                                'country': data.get('country'),
                                'timezone': data.get('timezone'),
                                'status': 'success'
                            }
                        else:
                            return {
                                'status': 'error',
                                'message': data.get('message', 'Invalid IP or location not found')
                            }
                    else:
                        return {
                            'status': 'error',
                            'message': f'HTTP error: {response.status}'
                        }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to get location for IP {ip_address}: {str(e)}'
            }
