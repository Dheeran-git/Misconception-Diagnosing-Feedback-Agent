"""FR6 — SymPy math-equivalence tool.

Two things:
1. ``math_equivalent(a, b)`` — a deterministic symbolic/numeric equivalence check
   used by the ASSESS and VERIFY steps (`grading.answers_equivalent`) so the agent
   trusts SymPy, not LLM arithmetic: "1/2" == "0.5", "2x+3" == "3+2*x",
   "x = 4" == "4".
2. ``math_check_server()`` — the same check exposed as a Claude Agent SDK custom
   tool, so a live agent turn can *call* it (see agent tool-use in
   `sdk_client.check_equivalence_via_agent`).

Everything degrades gracefully: unparseable input falls back to a normalized
string compare, never raising.
"""
from __future__ import annotations

from pydantic import BaseModel


class MathCheck(BaseModel):
    equivalent: bool
    method: str          # 'symbolic' | 'numeric' | 'string'
    detail: str = ""


def _normalize(s: str) -> str:
    """Lowercase, trim, and drop a leading 'var =' so 'x = 4' compares as '4'."""
    t = str(s).strip().lower()
    if "=" in t:
        t = t.split("=")[-1].strip()   # keep the right-hand side
    return t


def _parse(s: str):
    from sympy.parsing.sympy_parser import (
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )

    transformations = standard_transformations + (implicit_multiplication_application,)
    try:
        return parse_expr(s, transformations=transformations, evaluate=True)
    except Exception:
        return None


def math_equivalent(a: str, b: str) -> MathCheck:
    """Whether two answers are mathematically equivalent."""
    na, nb = _normalize(a), _normalize(b)
    if na == nb:
        return MathCheck(equivalent=True, method="string", detail="identical after normalization")

    import sympy

    ea, eb = _parse(na), _parse(nb)
    if ea is not None and eb is not None:
        try:
            diff = sympy.simplify(ea - eb)
            if diff == 0:
                return MathCheck(equivalent=True, method="symbolic", detail=f"{ea} == {eb}")
            # numeric fallback for things simplify won't close (e.g. floats vs rationals)
            val = complex(sympy.N(ea) - sympy.N(eb))
            if abs(val) < 1e-9:
                return MathCheck(equivalent=True, method="numeric", detail="numerically equal")
            return MathCheck(equivalent=False, method="symbolic", detail=f"{ea} != {eb}")
        except (TypeError, ValueError):
            pass  # non-numeric symbols etc. -> fall through to string compare

    return MathCheck(
        equivalent=(na == nb), method="string", detail="unparseable; compared as strings"
    )


# --------------------------------------------------------------------------- #
# Expose as a Claude Agent SDK custom tool
# --------------------------------------------------------------------------- #
def make_math_check_tool():
    """Build the SDK tool object (lazy import so offline code never needs the SDK)."""
    from claude_agent_sdk import tool

    @tool(
        "math_check",
        "Check whether two math answers/expressions are equivalent (uses SymPy).",
        {"a": str, "b": str},
    )
    async def _math_check(args):
        result = math_equivalent(args["a"], args["b"])
        return {"content": [{"type": "text", "text": result.model_dump_json()}]}

    return _math_check


def math_check_server():
    """An in-process MCP server exposing ``math_check`` to a live agent turn."""
    from claude_agent_sdk import create_sdk_mcp_server

    return create_sdk_mcp_server("math", tools=[make_math_check_tool()])
