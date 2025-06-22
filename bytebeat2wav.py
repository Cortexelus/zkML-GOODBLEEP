#!/usr/bin/env python3
"""
bytebeat2wav.py  –  Render a bytebeat formula to a 10-second 16 kHz mono WAV.

Usage
-----
python bytebeat2wav.py "t>>4 | (t&t>>5)" output.wav
"""
import argparse
import ast
import math
import wave
import numpy as np

# ---------- safe-eval helpers ----------
_ALLOWED_NAMES = {
    **{k: getattr(math, k) for k in dir(math) if not k.startswith("_")},
    "t": 0  # placeholder; replaced each iteration
}

class _SafeEval(ast.NodeTransformer):
    """Remove anything that isn't a basic expression (numbers, ops, names)."""
    _ALLOWED_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Name,
        ast.Call, ast.Load, ast.Pow, ast.Add, ast.Sub, ast.Mult, ast.Div,
        ast.Mod, ast.BitXor, ast.BitAnd, ast.BitOr, ast.RShift, ast.LShift,
        ast.FloorDiv
    )

    def generic_visit(self, node):
        if not isinstance(node, self._ALLOWED_NODES):
            raise ValueError(f"Illegal expression element: {ast.dump(node)}")
        return super().generic_visit(node)

def compile_formula(src: str):
    """Return a callable f(t) that is safe to evaluate."""
    tree = ast.parse(src, mode='eval')
    tree = _SafeEval().visit(tree)
    compiled = compile(ast.fix_missing_locations(tree), "<bytebeat>", "eval")
    def _f(t):
        _env = _ALLOWED_NAMES.copy()
        _env["t"] = t
        return eval(compiled, {"__builtins__": {}}, _env)
    return _f

# ---------- audio rendering ----------
def render(formula_str: str,
           sr: int = 16_000,
           secs: int = 10) -> np.ndarray:
    f = compile_formula(formula_str)
    t = np.arange(sr * secs, dtype=np.int64)
    # Evaluate formula vectorized: map python function over numpy array
    vfunc = np.vectorize(f, otypes=[np.int64])
    samples = vfunc(t) & 0xFF  # clamp to 8-bit (0-255) like classic bytebeat
    # Convert 0-255 → int16 centered at 0 (-32768 .. 32767)
    samples = (samples.astype(np.int16) - 128) << 8
    return samples

def write_wav(path: str, data: np.ndarray, sr: int = 16_000):
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Bytebeat → 16 kHz WAV")
    parser.add_argument("formula", help='Bytebeat expression, e.g. "t>>4|t&t>>5"')
    parser.add_argument("outfile", help="Output WAV filename")
    args = parser.parse_args()

    audio = render(args.formula)
    write_wav(args.outfile, audio)
    print(f"Saved {args.outfile} (10 s, 16 kHz mono)")

if __name__ == "__main__":
    main()
