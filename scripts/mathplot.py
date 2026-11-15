"""Deterministic SVG function plots for Memo-Canvas.

This is intentionally a small, self-contained renderer: no browser, no
GeoGebra, no symbolic algebra package, and no Python ``eval``.  Expressions
are parsed with a whitelist of arithmetic operations and functions.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sec": lambda value: 1 / math.cos(value),
    "csc": lambda value: 1 / math.sin(value),
    "cot": lambda value: 1 / math.tan(value),
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "ln": math.log,
    "log10": math.log10,
    "sqrt": math.sqrt,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
}
CONSTANTS = {"pi": math.pi, "e": math.e}
VARIABLES = {"x"}


class ExpressionError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    pos: int


def tokenize(expression: str) -> list[Token]:
    text = (expression.replace("π", "pi")
            .replace("−", "-")
            .replace("×", "*")
            .replace("÷", "/"))
    tokens: list[Token] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char.isspace():
            i += 1
            continue
        number = NUMBER_RE.match(text, i)
        if number:
            tokens.append(Token("number", number.group(0), i))
            i = number.end()
            continue
        name = NAME_RE.match(text, i)
        if name:
            tokens.append(Token("name", name.group(0), i))
            i = name.end()
            continue
        if text.startswith("**", i):
            tokens.append(Token("op", "^", i))
            i += 2
            continue
        if char in "+-*/^(),":
            tokens.append(Token("op", char, i))
            i += 1
            continue
        raise ExpressionError(f"Unexpected character {char!r} at position {i + 1}")
    tokens.append(Token("eof", "", len(text)))
    return tokens


class Parser:
    def __init__(self, expression: str):
        self.tokens = tokenize(expression)
        self.index = 0

    def peek(self) -> Token:
        return self.tokens[self.index]

    def take(self) -> Token:
        token = self.peek()
        self.index += 1
        return token

    def accept(self, value: str) -> bool:
        if self.peek().kind == "op" and self.peek().value == value:
            self.take()
            return True
        return False

    def parse(self):
        node = self.expression()
        if self.peek().kind != "eof":
            token = self.peek()
            raise ExpressionError(f"Unexpected token {token.value!r} at position {token.pos + 1}")
        return node

    def expression(self):
        node = self.term()
        while self.peek().kind == "op" and self.peek().value in "+-":
            op = self.take().value
            node = (op, node, self.term())
        return node

    def starts_primary(self) -> bool:
        token = self.peek()
        return token.kind in {"number", "name"} or (
            token.kind == "op" and token.value == "("
        )

    def term(self):
        node = self.unary()
        while True:
            token = self.peek()
            if token.kind == "op" and token.value in "*/":
                op = self.take().value
                node = (op, node, self.unary())
            elif self.starts_primary():
                # Implicit multiplication: 2sin(5x), x(x+1), 2pi.
                node = ("*", node, self.unary())
            else:
                return node

    def unary(self):
        if self.accept("+"):
            return self.unary()
        if self.accept("-"):
            return ("neg", self.unary())
        return self.power()

    def power(self):
        node = self.primary()
        if self.accept("^"):
            # Right associative: 2^3^2 == 2^(3^2).
            node = ("^", node, self.unary())
        return node

    def primary(self):
        token = self.take()
        if token.kind == "number":
            return ("number", float(token.value))
        if token.kind == "name":
            name = token.value
            if name in FUNCTIONS:
                if not self.accept("("):
                    raise ExpressionError(
                        f"Function {name!r} requires parentheses at position {token.pos + 1}"
                    )
                arg = self.expression()
                if not self.accept(")"):
                    raise ExpressionError(
                        f"Missing ')' for {name!r} at position {token.pos + 1}"
                    )
                return ("call", name, arg)
            if name in CONSTANTS:
                return ("number", CONSTANTS[name])
            if name in VARIABLES:
                return ("var", name)
            raise ExpressionError(f"Unknown name {name!r} at position {token.pos + 1}")
        if token.kind == "op" and token.value == "(":
            node = self.expression()
            if not self.accept(")"):
                raise ExpressionError(f"Missing ')' at position {token.pos + 1}")
            return node
        raise ExpressionError(f"Unexpected token {token.value!r} at position {token.pos + 1}")


def compile_expression(expression: str):
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("expression must be a non-empty string")
    return Parser(expression).parse()


def evaluate(node, x: float) -> float:
    kind = node[0]
    try:
        if kind == "number":
            return node[1]
        if kind == "var":
            return x
        if kind == "neg":
            return -evaluate(node[1], x)
        if kind == "call":
            return FUNCTIONS[node[1]](evaluate(node[2], x))
        left = evaluate(node[1], x)
        right = evaluate(node[2], x)
        if kind == "+":
            return left + right
        if kind == "-":
            return left - right
        if kind == "*":
            return left * right
        if kind == "/":
            return left / right
        if kind == "^":
            return left ** right
    except (ValueError, OverflowError, ZeroDivisionError):
        return math.nan
    return math.nan


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("range values must be finite")
    return str(int(value)) if value.is_integer() else repr(float(value))


def _label(item, axis: str, index: int):
    if isinstance(item, (int, float)):
        return {"value": float(item), "text": _number(float(item)), "dx": 0.0, "dy": 0.0}
    if not isinstance(item, dict):
        raise ValueError(f"{axis}_labels[{index}] must be a number or object")
    if "value" not in item or not isinstance(item["value"], (int, float)):
        raise ValueError(f"{axis}_labels[{index}].value must be a number")
    value = float(item["value"])
    text = item.get("text", _number(value))
    if not isinstance(text, str) or not text:
        raise ValueError(f"{axis}_labels[{index}].text must be a non-empty string")
    dx = item.get("dx", 0)
    dy = item.get("dy", 0)
    if not isinstance(dx, (int, float)) or not isinstance(dy, (int, float)):
        raise ValueError(f"{axis}_labels[{index}].dx/dy must be numbers")
    return {"value": value, "text": text, "dx": float(dx), "dy": float(dy)}


def load_config(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Config root must be an object")

    allowed = {
        "expression", "xrange", "yrange", "width", "height", "samples",
        "color", "axis_color", "background", "line_width", "axis_width",
        "font_size", "margin", "x_labels", "y_labels",
        "axis_arrows", "arrow_size", "axis_names", "show_ticks",
        "title", "title_color", "title_dx", "title_dy", "y_label_side",
    }
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError("Unknown config field(s): " + ", ".join(unknown))

    expression = data.get("expression")
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    compile_expression(expression)

    def pair(name, default):
        value = data.get(name, default)
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError(f"{name} must be [min, max]")
        if not all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in value):
            raise ValueError(f"{name} must contain two finite numbers")
        lo, hi = float(value[0]), float(value[1])
        if not lo < hi:
            raise ValueError(f"{name} min must be less than max")
        return lo, hi

    xrange = pair("xrange", [-6, 6])
    yrange = pair("yrange", [-5, 5])

    width = data.get("width", 1600)
    height = data.get("height", 900)
    samples = data.get("samples", 4000)
    margin = data.get("margin", 64)
    font_size = data.get("font_size", 20)
    line_width = data.get("line_width", 3)
    axis_width = data.get("axis_width", 2)
    for name, value, minimum, maximum in [
        ("width", width, 200, 10000),
        ("height", height, 120, 10000),
        ("samples", samples, 16, 200000),
        ("margin", margin, 0, 500),
        ("font_size", font_size, 8, 200),
        ("line_width", line_width, 0.5, 40),
        ("axis_width", axis_width, 0.5, 40),
    ]:
        if not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")

    color = data.get("color", "#36B59D")
    axis_color = data.get("axis_color", "#8E8E8E")
    background = data.get("background", "transparent")
    for name, value in [("color", color), ("axis_color", axis_color)]:
        if not isinstance(value, str) or not HEX_RE.fullmatch(value):
            raise ValueError(f"{name} must be a six-digit hex color")
    if background != "transparent" and (
        not isinstance(background, str) or not HEX_RE.fullmatch(background)
    ):
        raise ValueError("background must be 'transparent' or a six-digit hex color")

    axis_arrows = data.get("axis_arrows", False)
    show_ticks = data.get("show_ticks", False)
    if not isinstance(axis_arrows, bool):
        raise ValueError("axis_arrows must be boolean")
    if not isinstance(show_ticks, bool):
        raise ValueError("show_ticks must be boolean")

    arrow_size = data.get("arrow_size", 12)
    if not isinstance(arrow_size, int) or not 4 <= arrow_size <= 40:
        raise ValueError("arrow_size must be an integer from 4 to 40")

    axis_names = data.get("axis_names", {})
    if not isinstance(axis_names, dict) or set(axis_names) - {"x", "y"}:
        raise ValueError("axis_names may contain only x and y")
    for key, value in axis_names.items():
        if not isinstance(value, str):
            raise ValueError(f"axis_names.{key} must be a string")
    title = data.get("title")
    if title is not None and not isinstance(title, str):
        raise ValueError("title must be a string")
    title_color = data.get("title_color", color)
    if not isinstance(title_color, str) or not HEX_RE.fullmatch(title_color):
        raise ValueError("title_color must be a six-digit hex color")
    title_dx = data.get("title_dx", 0)
    title_dy = data.get("title_dy", 0)
    if not isinstance(title_dx, (int, float)) or not isinstance(title_dy, (int, float)):
        raise ValueError("title_dx/title_dy must be numbers")
    y_label_side = data.get("y_label_side", "right")
    if y_label_side not in {"left", "right"}:
        raise ValueError("y_label_side must be 'left' or 'right'")

    x_labels = data.get("x_labels", [])
    y_labels = data.get("y_labels", [])
    if not isinstance(x_labels, list) or not isinstance(y_labels, list):
        raise ValueError("x_labels and y_labels must be arrays")

    return {
        "expression": expression,
        "xrange": xrange,
        "yrange": yrange,
        "width": width,
        "height": height,
        "samples": samples,
        "margin": margin,
        "font_size": font_size,
        "line_width": line_width,
        "axis_width": axis_width,
        "color": color,
        "axis_color": axis_color,
        "background": background,
        "x_labels": [_label(item, "x", i) for i, item in enumerate(x_labels)],
        "y_labels": [_label(item, "y", i) for i, item in enumerate(y_labels)],
        "axis_arrows": axis_arrows,
        "arrow_size": arrow_size,
        "axis_names": axis_names,
        "show_ticks": show_ticks,
        "title": title,
        "title_color": title_color,
        "title_dx": float(title_dx),
        "title_dy": float(title_dy),
        "y_label_side": y_label_side,
    }


def sample(config):
    node = compile_expression(config["expression"])
    xmin, xmax = config["xrange"]
    ymin, ymax = config["yrange"]
    count = config["samples"]
    segments = []
    current = []
    for index in range(count):
        x = xmin + (xmax - xmin) * index / (count - 1)
        y = evaluate(node, x)
        if (not isinstance(y, (int, float)) or not math.isfinite(y)
                or y < ymin or y > ymax):
            if len(current) > 1:
                segments.append(current)
            current = []
            continue
        current.append((x, y))
    if len(current) > 1:
        segments.append(current)
    if not segments:
        raise ValueError("No finite function values inside yrange; adjust yrange or expression")
    return segments


def svg_document(config, segments):
    width, height = config["width"], config["height"]
    margin = config["margin"]
    xmin, xmax = config["xrange"]
    ymin, ymax = config["yrange"]
    plot_w = width - 2 * margin
    plot_h = height - 2 * margin
    if plot_w <= 0 or plot_h <= 0:
        raise ValueError("margin leaves no plot area")

    def px(x):
        return margin + (x - xmin) * plot_w / (xmax - xmin)

    def py(y):
        return height - margin - (y - ymin) * plot_h / (ymax - ymin)

    paths = []
    for segment in segments:
        path = "M " + " L ".join(
            f"{px(x):.2f} {py(y):.2f}" for x, y in segment
        )
        paths.append(path)

    background = ""
    if config["background"] != "transparent":
        background = (
            f'<rect x="0" y="0" width="{width}" height="{height}" '
            f'fill="{html.escape(config["background"])}"/>'
        )

    axes = []
    has_x_axis = ymin <= 0 <= ymax
    has_y_axis = xmin <= 0 <= xmax
    axis_y = py(0)
    axis_x = px(0)
    axis_color = html.escape(config["axis_color"])
    if has_x_axis:
        axes.append(
            f'<line x1="{margin}" y1="{axis_y:.2f}" x2="{width - margin}" '
            f'y2="{axis_y:.2f}" stroke="{axis_color}" '
            f'stroke-width="{config["axis_width"]}"/>'
        )
    if has_y_axis:
        axes.append(
            f'<line x1="{axis_x:.2f}" y1="{margin}" x2="{axis_x:.2f}" '
            f'y2="{height - margin}" stroke="{axis_color}" '
            f'stroke-width="{config["axis_width"]}"/>'
        )

    if config["axis_arrows"]:
        size = config["arrow_size"]
        half = size * 0.45
        if has_x_axis:
            axes.append(
                f'<path d="M {width - margin} {axis_y:.2f} '
                f'L {width - margin - size} {axis_y - half:.2f} '
                f'L {width - margin - size} {axis_y + half:.2f} Z" '
                f'fill="{axis_color}"/>'
            )
            axes.append(
                f'<path d="M {margin} {axis_y:.2f} '
                f'L {margin + size} {axis_y - half:.2f} '
                f'L {margin + size} {axis_y + half:.2f} Z" '
                f'fill="{axis_color}"/>'
            )
        if has_y_axis:
            axes.append(
                f'<path d="M {axis_x:.2f} {margin} '
                f'L {axis_x - half:.2f} {margin + size} '
                f'L {axis_x + half:.2f} {margin + size} Z" '
                f'fill="{axis_color}"/>'
            )
            axes.append(
                f'<path d="M {axis_x:.2f} {height - margin} '
                f'L {axis_x - half:.2f} {height - margin - size} '
                f'L {axis_x + half:.2f} {height - margin - size} Z" '
                f'fill="{axis_color}"/>'
            )

    ticks = []
    if config["show_ticks"]:
        for item in config["x_labels"]:
            if has_x_axis and xmin <= item["value"] <= xmax:
                x = px(item["value"])
                ticks.append(
                    f'<line x1="{x:.2f}" y1="{axis_y - 6:.2f}" '
                    f'x2="{x:.2f}" y2="{axis_y + 6:.2f}" '
                    f'stroke="{axis_color}" stroke-width="{config["axis_width"]}"/>'
                )
        for item in config["y_labels"]:
            if has_y_axis and ymin <= item["value"] <= ymax:
                y = py(item["value"])
                ticks.append(
                    f'<line x1="{axis_x - 6:.2f}" y1="{y:.2f}" '
                    f'x2="{axis_x + 6:.2f}" y2="{y:.2f}" '
                    f'stroke="{axis_color}" stroke-width="{config["axis_width"]}"/>'
                )

    labels = []
    for item in config["x_labels"]:
        if not (xmin <= item["value"] <= xmax):
            continue
        x = px(item["value"])
        y = (axis_y if has_x_axis else height - margin) + config["font_size"] * 1.3
        labels.append(
            f'<text x="{x + item["dx"]:.2f}" y="{y + item["dy"]:.2f}" '
            f'text-anchor="middle" fill="{axis_color}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{config["font_size"]}">{html.escape(item["text"])}</text>'
        )
    label_axis_x = axis_x if has_y_axis else margin
    y_label_anchor = "end" if config["y_label_side"] == "left" else "start"
    y_label_offset = -config["font_size"] * 0.4 if config["y_label_side"] == "left" else config["font_size"] * 0.7
    for item in config["y_labels"]:
        if not (ymin <= item["value"] <= ymax):
            continue
        labels.append(
            f'<text x="{label_axis_x + y_label_offset + item["dx"]:.2f}" '
            f'y="{py(item["value"]) + item["dy"]:.2f}" '
            f'text-anchor="{y_label_anchor}" fill="{axis_color}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{config["font_size"]}">{html.escape(item["text"])}</text>'
        )

    names = []
    if has_y_axis and config["axis_names"].get("y"):
        names.append(
            f'<text x="{axis_x + config["font_size"] * 0.6:.2f}" '
            f'y="{margin + config["font_size"] * 1.15:.2f}" '
            f'text-anchor="start" fill="{axis_color}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{config["font_size"]}">{html.escape(config["axis_names"]["y"])}</text>'
        )
    if has_x_axis and config["axis_names"].get("x"):
        names.append(
            f'<text x="{width - margin - config["font_size"] * 0.3:.2f}" '
            f'y="{axis_y - config["font_size"] * 0.7:.2f}" '
            f'text-anchor="end" fill="{axis_color}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{config["font_size"]}">{html.escape(config["axis_names"]["x"])}</text>'
        )
    if config["title"]:
        names.append(
            f'<text x="{width - margin + config["title_dx"]:.2f}" '
            f'y="{margin + config["font_size"] * 1.15 + config["title_dy"]:.2f}" '
            f'text-anchor="end" fill="{html.escape(config["title_color"])}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif" '
            f'font-size="{config["font_size"]}">{html.escape(config["title"])}</text>'
        )

    path_markup = "\n".join(
        f'<path d="{path}" fill="none" stroke="{html.escape(config["color"])}" '
        f'stroke-width="{config["line_width"]}" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        for path in paths
    )
    label_markup = "\n".join(labels + names)
    tick_markup = "\n".join(ticks)
    axis_markup = "\n".join(axes)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><clipPath id="mathplot-clip"><rect x="{margin}" y="{margin}" width="{plot_w}" height="{plot_h}"/></clipPath></defs>
{background}
<g clip-path="url(#mathplot-clip)">
{path_markup}
{axis_markup}
{tick_markup}
</g>
{label_markup}
</svg>
'''


def run_mathplot(args):
    config_path = Path(args.input).resolve(strict=True)
    config = load_config(config_path)
    segments = sample(config)
    svg = svg_document(config, segments)

    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError(f"Refusing to overwrite: {output}")
    if output.suffix.lower() not in {'.png', '.svg'}:
        raise ValueError("output must end in .png or .svg")
    output.parent.mkdir(parents=True, exist_ok=True)

    base = {
        'mode': 'mathplot',
        'expression': config['expression'],
        'xrange': list(config['xrange']),
        'yrange': list(config['yrange']),
        'samples': config['samples'],
        'segments': len(segments),
        'source_verified': False,
        'visual_audit': 'not_checked',
        'note': 'Deterministic sampled SVG plot; verify labels and clipping for the target card.',
    }

    if output.suffix.lower() == '.svg':
        sidecar = output.with_name(output.name + '.json')
        if sidecar.exists():
            raise ValueError(f"Refusing to overwrite: {sidecar}")
        output.write_text(svg, encoding='utf-8')
        base.update({'output': str(output), 'svg': str(output)})
        sidecar.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
        return base

    source_svg = output.with_name(output.name + '.source.svg')
    metadata = output.with_name(output.name + '.json')
    for target in (source_svg, metadata):
        if target.exists():
            raise ValueError(f"Refusing to overwrite: {target}")

    node = shutil.which('node')
    if not node:
        raise ValueError('Node.js >=20 required for SVG rasterization; use a .svg output or run setup')

    # canvas_render.cjs writes the PNG, a .source.svg sidecar, and a .json
    # sidecar. Feed it a temporary SVG so it owns those sidecars without a
    # pre-existing source file blocking its wx write.
    temp = output.with_name(output.name + '.mathplot-input.svg')
    if temp.exists():
        raise ValueError(f"Refusing to overwrite: {temp}")
    temp.write_text(svg, encoding='utf-8')
    try:
        subprocess.run(
            [node, str(ROOT / 'scripts/canvas_render.cjs'), 'svg',
             str(temp), str(output), '32', '72'],
            check=True, timeout=120,
        )
    finally:
        temp.unlink(missing_ok=True)

    base.update({'output': str(output), 'svg': str(source_svg)})
    metadata.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding='utf-8')
    return base


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run_mathplot(args), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Cannot complete mathplot: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
