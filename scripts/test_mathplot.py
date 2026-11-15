import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mathplot import ExpressionError, compile_expression, evaluate, load_config, sample  # noqa: E402


class MathplotTests(unittest.TestCase):
    def test_implicit_multiplication_and_power(self):
        node = compile_expression("sin(x^2)cos(3x)+2sin(5x)/(1+x^2)+x/4")
        x = 0.3
        expected = (math.sin(x ** 2) * math.cos(3 * x)
                    + 2 * math.sin(5 * x) / (1 + x ** 2)
                    + x / 4)
        self.assertAlmostEqual(evaluate(node, x), expected, places=12)

    def test_power_is_right_associative_and_unary_binds_after_power(self):
        self.assertAlmostEqual(evaluate(compile_expression("2^3^2"), 0), 512)
        self.assertAlmostEqual(evaluate(compile_expression("-x^2"), 3), -9)
        self.assertAlmostEqual(evaluate(compile_expression("(-x)^2"), 3), 9)

    def test_constants_and_unicode(self):
        self.assertAlmostEqual(evaluate(compile_expression("2π"), 0), 2 * math.pi)
        self.assertAlmostEqual(evaluate(compile_expression("sin(−π/2)"), 0), -1)

    def test_sec_csc_cot(self):
        self.assertAlmostEqual(evaluate(compile_expression("sec(0)"), 0), 1)
        self.assertAlmostEqual(evaluate(compile_expression("csc(pi/2)"), 0), 1)
        self.assertAlmostEqual(evaluate(compile_expression("cot(pi/4)"), 0), 1)

    def test_unknown_name_rejected(self):
        with self.assertRaises(ExpressionError):
            compile_expression("sin(x)+secret(x)")

    def test_invalid_config_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"expression": "x", "yrange": [5, -5]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_svg_output_and_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            config = temp / "config.json"
            config.write_text(json.dumps({
                "expression": "sin(x^2)cos(3x)+2sin(5x)/(1+x^2)+x/4",
                "xrange": [-6, 6],
                "yrange": [-5, 5],
                "width": 800,
                "height": 450,
                "samples": 1000,
                "color": "#36B59D",
                "x_labels": [{"value": -math.pi, "text": "−π"}, {"value": math.pi, "text": "π"}],
                "y_labels": [{"value": -1, "text": "-1"}, {"value": 1, "text": "1"}],
            }), encoding="utf-8")
            output = temp / "plot.svg"
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "canvas.py"),
                            "mathplot", "--input", str(config), "--output", str(output)],
                           check=True, capture_output=True, text=True)
            svg = output.read_text(encoding="utf-8")
            self.assertIn('stroke="#36B59D"', svg)
            self.assertIn("−π", svg)
            self.assertIn(">π</text>", svg)
            self.assertIn(">-1</text>", svg)
            self.assertIn(">1</text>", svg)
            self.assertNotIn(">0</text>", svg)

    def test_style_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            config = temp / "style.json"
            config.write_text(json.dumps({
                "expression": "asin(x)",
                "xrange": [-1.55, 1.55],
                "yrange": [-2.2, 2.2],
                "width": 700,
                "height": 850,
                "samples": 500,
                "color": "#36B59D",
                "line_width": 5,
                "axis_arrows": True,
                "arrow_size": 14,
                "axis_names": {"x": "x", "y": "y"},
                "show_ticks": True,
                "y_label_side": "left",
                "title": "y = arcsin(x)",
                "title_color": "#36B59D",
                "x_labels": [{"value": -1, "text": "-1"}, {"value": 0, "text": "0"}, {"value": 1, "text": "1"}],
                "y_labels": [{"value": -1.5707963267948966, "text": "−π/2"},
                             {"value": 1.5707963267948966, "text": "π/2"}],
            }), encoding="utf-8")
            output = temp / "style.svg"
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "canvas.py"),
                            "mathplot", "--input", str(config), "--output", str(output)],
                           check=True, capture_output=True, text=True)
            svg = output.read_text(encoding="utf-8")
            self.assertIn("y = arcsin(x)", svg)
            self.assertIn(">x</text>", svg)
            self.assertIn(">y</text>", svg)
            self.assertIn('fill="#36B59D"', svg)
            self.assertIn('text-anchor="end"', svg)
            self.assertGreaterEqual(svg.count("<path"), 1)
            self.assertGreaterEqual(svg.count("<line"), 4)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            config = temp / "config.json"
            config.write_text(json.dumps({"expression": "x"}), encoding="utf-8")
            output = temp / "plot.svg"
            output.write_text("existing", encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "canvas.py"),
                                     "mathplot", "--input", str(config), "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing to overwrite", result.stderr)


if __name__ == "__main__":
    unittest.main()
