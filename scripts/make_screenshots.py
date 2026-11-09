"""Render real command output as terminal-style PNGs (headless Chrome). python3 scripts/make_screenshots.py"""
import html, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def sh(cmd):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    return f"$ {cmd}\n{p.stdout}{p.stderr}"


demo = subprocess.run([sys.executable, "demo.py"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
model = [l for l in demo if l.startswith("model:")]
gen = [l for l in demo if l.startswith(("generated", "reference"))]
kill = demo[len(model) + len(gen):]
shots = {
    "1_model_execution": "$ python3 demo.py   # part 1: executable state-machine model\n" + "\n".join(model),
    "2_generation_and_execution": "$ python3 demo.py   # part 2: generate + execute (transition_pair)\n" + "\n".join(gen),
    "3_fault_detection": "$ python3 demo.py   # part 3: injected fault M05 detected\n" + "\n".join(kill),
    "4_unit_tests": sh("python3 -m unittest discover -s tests -v 2>&1 | tail -16"),
    "5_experiment_results": "$ cat results/summary.md   # from: python3 -m locker.experiment\n" + (ROOT / "results/summary.md").read_text().split("Per mutant")[0],
}
for name, text in shots.items():
    page = OUT / f"{name}.html"
    page.write_text(f"<html><body style='margin:0;background:#1e1e1e;overflow:hidden'><pre style='color:#ddd;font:14px/1.4 monospace;"
                    f"padding:16px;margin:0;white-space:pre-wrap;word-break:break-all;width:1100px'>{html.escape(text)}</pre></body></html>")
    h = 90 + 22 * sum(len(l) // 115 + 1 for l in text.splitlines())
    subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size=1132,{h}",
                    f"--screenshot={OUT / (name + '.png')}", page.as_uri()], capture_output=True)
    page.unlink()
    print("wrote", OUT / f"{name}.png")
