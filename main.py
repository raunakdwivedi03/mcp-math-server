# main.py — FastMCP arithmetic server
from __future__ import annotations
from fastmcp import FastMCP

mcp = FastMCP("arith")

def _as_number(x):
    # Accept ints/floats or numeric strings; raise clean errors otherwise
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip())
    raise TypeError("Expected a number (int/float or numeric string)")

@mcp.tool()
async def add(a: float, b: float) -> float:
    """Return a + b."""
    return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float, b: float) -> float:
    """Return a - b."""
    return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float, b: float) -> float:
    """Return a * b."""
    return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float, b: float) -> float:
    """Return a / b."""
    a_val = _as_number(a)
    b_val = _as_number(b)
    if b_val == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a_val / b_val

if __name__ == "__main__":
    mcp.run()