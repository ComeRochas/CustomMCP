"""Calculator tools implementation."""

from typing import Union

class CalculatorTools:
    """Calculator operations for the MCP server."""
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Add two numbers together."""
        return a + b
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Subtract second number from first."""
        return a - b
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
        """Divide first number by second."""
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return a / b
    
    def power(self, base: Union[int, float], exponent: Union[int, float]) -> Union[int, float]:
        """Raise base to the power of exponent."""
        return base ** exponent