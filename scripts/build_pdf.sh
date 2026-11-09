#!/bin/sh
# REPORT.md -> REPORT.pdf (needs pandoc + google-chrome). Run from project root.
set -e
cat > "${TMPDIR:-/tmp}/rep.css" <<'CSS'
body{font:11pt/1.45 sans-serif;max-width:none;margin:0}
table{border-collapse:collapse;font-size:9pt;margin:8px 0}td,th{border:1px solid #999;padding:3px 6px}
img{max-width:100%}code{font-size:9pt}pre{white-space:pre-wrap}
CSS
pandoc REPORT.md -s --embed-resources --metadata title="Model-Based Testing of a Smart Parcel Locker" -c "${TMPDIR:-/tmp}/rep.css" -o "${TMPDIR:-/tmp}/rep.html"
google-chrome --headless --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf=REPORT.pdf "file://${TMPDIR:-/tmp}/rep.html"
