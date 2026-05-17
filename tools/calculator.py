import math


def calculator(expression: str):
    """
    简单数学计算
    """
    try:
        allowed_names = {
            "abs": abs,
            "round": round,
            "max": max,
            "min": min,
            "pow": pow,
            "sqrt": math.sqrt,
        }

        result = eval(expression, {"__builtins__": {}}, allowed_names)

        return {
            "success": True,
            "result": result,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
