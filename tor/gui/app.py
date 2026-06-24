#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import (Flask, Response, jsonify, render_template,
                   request, stream_with_context)

VECTOR_ROOT = Path(os.environ.get("VECTOR_ROOT", Path(__file__).parent.parent)).resolve()
sys.path.insert(0, str(VECTOR_ROOT))

app = Flask(__name__)

_scans: dict[str, dict] = {}
_scans_lock = threading.Lock()

SCAN_STATUS_PENDING = "pending"
SCAN_STATUS_RUNNING = "running"
SCAN_STATUS_DONE    = "done"
SCAN_STATUS_FAILED  = "failed"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_scan(scan_id: str) -> dict | None:
    with _scans_lock:
        return _scans.get(scan_id)


def _update_scan(scan_id: str, **kwargs) -> None:
    with _scans_lock:
        if scan_id in _scans:
            _scans[scan_id].update(kwargs)


def _append_output(scan_id: str, line: str) -> None:
    with _scans_lock:
        if scan_id in _scans:
            _scans[scan_id]["output_lines"].append(line)


def _new_scan_record(scan_type: str, target: str, app_name: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": scan_type,
        "target": target,
        "app_name": app_name,
        "status": SCAN_STATUS_PENDING,
        "submitted_at": _now_iso(),
        "finished_at": None,
        "output_lines": [],
        "cbom_files": [],
        "scored_cbom": None,
        "report_md": None,
        "report_html": None,
        "cbom_html": None,
        "raw_html": None,
        "raw_scan": None,
        "error": None,
        "exit_code": None,
    }



def _md_to_html(md: str) -> str:
    import re
    import html as _html

    BADGE = {
        'quantum-vulnerable':    'badge--red',
        'classically-deprecated':'badge--red',
        'non-hybrid':            'badge--amber',
        'quantum-safe':          'badge--green',
        'hybrid':                'badge--blue',
        'unknown':               'badge--gray',
    }
    RISK_SCORE = {
        'High':   'risk-score--high',
        'Medium': 'risk-score--medium',
        'Low':    'risk-score--low',
        'None':   'risk-score--none',
    }

    lines = md.split('\n')
    out = []
    in_table  = False
    is_header = False
    in_section = False

    def badge(cls_name):
        css = BADGE.get(cls_name, 'badge--gray')
        return f'<span class="badge {css}">{_html.escape(cls_name)}</span>'

    def risk_badge(label):
        css = RISK_SCORE.get(label, '')
        if css:
            return f'<span class="risk-score {css}">{_html.escape(label)}</span>'
        return _html.escape(label)

    def render_cell(text: str) -> str:
        text = text.strip()
        if text in BADGE:
            return badge(text)
        if text in RISK_SCORE:
            return risk_badge(text)
        text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<strong>{_html.escape(m.group(1))}</strong>', text)
        text = re.sub(r'`([^`]+)`', lambda m: f'<code class="inline-code">{_html.escape(m.group(1))}</code>', text)
        text = text.replace('<br>', '<br>')
        return text

    def render_inline(text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', lambda m: f'<strong>{_html.escape(m.group(1))}</strong>', text)
        text = re.sub(r'`([^`]+)`', lambda m: f'<code class="inline-code">{_html.escape(m.group(1))}</code>', text)
        for label, css in RISK_SCORE.items():
            text = re.sub(rf'\b{label}\b', f'<span class="risk-score {css}">{label}</span>', text)
        return text

    def close_section():
        nonlocal in_section
        if in_section:
            out.append('</div></details>')
            in_section = False

    for line in lines:
        stripped = line.strip()

        is_row = stripped.startswith('|') and stripped.endswith('|')
        is_sep = is_row and re.match(r'^[\|\s\-:]+$', stripped)

        if is_row and not is_sep:
            if not in_table:
                out.append('<div class="table-wrap"><table class="data-table"><thead>')
                in_table  = True
                is_header = True
            elif is_header:
                out.append('</thead><tbody>')
                is_header = False
            cells = [c.strip() for c in stripped[1:-1].split('|')]
            tag = 'th' if is_header else 'td'
            out.append('<tr>' + ''.join(f'<{tag}>{render_cell(c)}</{tag}>' for c in cells) + '</tr>')
            continue

        if is_sep:
            continue

        if in_table:
            out.append('</tbody></table></div>')
            in_table = False
            is_header = False

        m = re.match(r'^(#{1,4}) (.+)$', line)
        if m:
            level = len(m.group(1))
            text  = render_inline(m.group(2).strip())
            if level == 1:
                close_section()
                out.append(f'<h1 class="report-h1">{text}</h1>')
            else:
                close_section()
                tag = f'h{level}'
                cls = f'report-h{level}'
                out.append(f'<details class="report-section" open>')
                out.append(f'<summary class="report-section__summary"><{tag} class="{cls}">{text}</{tag}></summary>')
                out.append('<div class="report-section__body">')
                in_section = True
            continue

        if re.match(r'^- (.+)$', line):
            content = render_inline(line[2:].strip())
            out.append(f'<li>{content}</li>')
            continue

        if stripped == '':
            out.append('<br>')
            continue

        out.append(render_inline(line))

    if in_table:
        out.append('</tbody></table></div>')
    close_section()

    return '\n'.join(out)


def _build_cbom_html(scored_cbom: dict) -> str:
    import html as _h
    BADGE = {
        'quantum-vulnerable':    'badge--red',
        'classically-deprecated':'badge--red',
        'non-hybrid':            'badge--amber',
        'quantum-safe':          'badge--green',
        'hybrid':                'badge--blue',
        'unknown':               'badge--gray',
    }
    RISK_SCORE_CLASS = {
        'high':   'risk-score--high',
        'medium': 'risk-score--medium',
        'low':    'risk-score--low',
        'none':   'risk-score--none',
    }

    def prop(props, name):
        for p in props:
            if p.get('name') == name:
                return p.get('value', '')
        return ''

    components = [
        c for c in scored_cbom.get('components', [])
        if c.get('cryptoProperties', {}).get('assetType') == 'algorithm'
    ]
    if not components:
        return '<div class="empty-state"><div class="empty-state__title">No algorithm components found</div></div>'

    cards = []
    for comp in components:
        ap = comp.get('cryptoProperties', {}).get('algorithmProperties', {})
        props = comp.get('properties', [])
        classification = prop(props, 'pqcmat:risk-classification') or 'unknown'
        risk_score = prop(props, 'pqcmat:risk-score') or 'unknown'
        rationale = prop(props, 'pqcmat:rationale')
        migration = prop(props, 'pqcmat:recommended-migration')
        refs = [p.get('value', '') for p in props if p.get('name') == 'pqcmat:reference']
        variant = _h.escape(ap.get('variant') or comp.get('name') or '—')
        primitive = _h.escape(ap.get('primitive') or '—')
        key_size = _h.escape(ap.get('parameterSetIdentifier') or ap.get('keySize') or '')
        mode = _h.escape(ap.get('mode') or '')
        badge_cls = BADGE.get(classification, 'badge--gray')
        score_cls = RISK_SCORE_CLASS.get(risk_score, '')
        dc = (comp.get('cryptoProperties', {}).get('detectionContext') or [{}])[0]
        file_path = _h.escape(dc.get('filePath') or '')
        line_nums = ', '.join(str(n) for n in (dc.get('lineNumbers') or []))

        h  = f'<div class="cbom-card" data-classification="{_h.escape(classification)}">'
        h += f'<div class="cbom-card__header">'
        h += f'<span class="cbom-card__name">{variant}</span>'
        h += f'<span class="badge {badge_cls}">{_h.escape(classification)}</span>'
        h += f'</div>'
        h += f'<div class="cbom-card__meta">'
        h += f'<span class="cbom-meta-item"><span class="cbom-meta-label">Primitive</span>{primitive}</span>'
        if key_size:
            h += f'<span class="cbom-meta-item"><span class="cbom-meta-label">Key size</span>{key_size}</span>'
        if mode and mode != 'unknown':
            h += f'<span class="cbom-meta-item"><span class="cbom-meta-label">Mode</span>{mode}</span>'
        h += f'<span class="cbom-meta-item"><span class="cbom-meta-label">Risk</span>'
        h += f'<span class="risk-score {score_cls}">{risk_score.upper()}</span></span>'
        h += f'</div>'
        if rationale:
            h += f'<div class="cbom-card__rationale">{_h.escape(rationale)}</div>'
        if migration:
            h += f'<div class="cbom-card__migration"><span class="cbom-migration-label">Migration →</span> {_h.escape(migration)}</div>'
        if file_path:
            loc = f'{file_path}:{line_nums}' if line_nums else file_path
            h += f'<div class="cbom-card__location"><code class="inline-code">{loc}</code></div>'
        if refs:
            ref_spans = ''.join(f'<span class="cbom-ref">{_h.escape(r)}</span>' for r in refs if r)
            h += f'<div class="cbom-card__refs">{ref_spans}</div>'
        h += '</div>'
        cards.append(h)

    return '\n'.join(cards)


def _build_raw_html(raw_data, max_depth: int = 4) -> str:
    import html as _h
    import json as _json

    def node(obj, depth=0):
        if depth >= max_depth:
            if isinstance(obj, str):
                return f'<span class="json-string">"{_h.escape(obj)}"</span>'
            return f'<span class="json-bool">{_h.escape(_json.dumps(obj))}</span>'

        if isinstance(obj, list):
            inner = ''.join(f'<div class="json-row"><span class="json-key">{i}: </span>{node(v, depth+1)}</div>' for i, v in enumerate(obj))
            return f'<details {"open" if depth < 2 else ""}><summary class="json-summary">Array [{len(obj)}]</summary>{inner}</details>'

        if isinstance(obj, dict):
            inner = ''.join(f'<div class="json-row"><span class="json-key">{_h.escape(str(k))}: </span>{node(v, depth+1)}</div>' for k, v in obj.items())
            return f'<details {"open" if depth < 2 else ""}><summary class="json-summary">Object {{{len(obj)}}}</summary>{inner}</details>'

        if isinstance(obj, str):
            return f'<span class="json-string">"{_h.escape(obj)}"</span>'
        if isinstance(obj, (int, float)):
            return f'<span class="json-number">{obj}</span>'
        return f'<span class="json-bool">{_h.escape(str(obj))}</span>'

    return f'<div class="json-node">{node(raw_data)}</div>'


def _score_cboms(scan_id: str, cbom_paths: list[str]) -> None:
    import traceback as _tb
    _append_output(scan_id, "")
    _append_output(scan_id, "Running VECTOR-Score")
    try:
        from tor.vector_score.cbom_scorer import score_cbom
        from tor.vector_score.report_generator import generate_report

        all_scored = []
        for cbom_path in cbom_paths:
            try:
                with open(cbom_path, "r", encoding="utf-8") as f:
                    cbom = json.load(f)
                scored = score_cbom(cbom)
                all_scored.append(scored)
                _append_output(scan_id, f"  Scored: {Path(cbom_path).name}")
            except Exception as exc:
                _append_output(scan_id, f"  Error scoring {Path(cbom_path).name}: {exc}")
                for ln in _tb.format_exc().splitlines():
                    _append_output(scan_id, f"    {ln}")

        if not all_scored:
            _append_output(scan_id, "  No CBOMs were scored successfully")
            return

        merged = all_scored[0]
        for extra in all_scored[1:]:
            merged["components"].extend(extra.get("components", []))

        _append_output(scan_id, "  Generating report")
        try:
            report_md = generate_report(merged)
        except Exception as exc:
            _append_output(scan_id, f"  Error generating report: {exc}")
            for ln in _tb.format_exc().splitlines():
                _append_output(scan_id, f"    {ln}")
            report_md = None

        report_html = None
        if report_md:
            try:
                report_html = _md_to_html(report_md)
            except Exception as exc:
                _append_output(scan_id, f"  Error rendering HTML: {exc}")
                for ln in _tb.format_exc().splitlines():
                    _append_output(scan_id, f"    {ln}")

        _update_scan(scan_id, scored_cbom=merged, report_md=report_md, report_html=report_html,
                         cbom_html=_build_cbom_html(merged))
        _append_output(scan_id, f"  Components scored: {len(merged.get('components', []))}")
        if report_md:
            _append_output(scan_id, f"  Report generated: {len(report_md)} chars")

    except ImportError as exc:
        _append_output(scan_id, f"  VECTOR-Score not available: {exc}")
    except Exception as exc:
        _append_output(scan_id, f"  Scoring failed: {exc}")
        for ln in _tb.format_exc().splitlines():
            _append_output(scan_id, f"    {ln}")


def _run_code_scan(scan_id: str, source: str, app_name: str) -> None:
    _update_scan(scan_id, status=SCAN_STATUS_RUNNING)
    _append_output(scan_id, f"Starting VECTOR-Code scan: {source}")

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable, "-m", "tor.vector_code.main",
            source, "--name", app_name,
        ]

        proc = subprocess.Popen(
            cmd,
            cwd=str(VECTOR_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        for line in proc.stdout:
            _append_output(scan_id, line.rstrip("\n"))
        proc.wait()
        exit_code = proc.returncode
        _update_scan(scan_id, exit_code=exit_code)

        if exit_code == 0:
            cbom_dir = VECTOR_ROOT / "tor" / "vector_code" / "output" / "cbom"
            cbom_files = sorted(cbom_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if cbom_dir.exists() else []
            _update_scan(scan_id, cbom_files=[str(p) for p in cbom_files])

            if cbom_files:
                _score_cboms(scan_id, [str(p) for p in cbom_files])

            if cbom_files:
                raw_data = json.loads(Path(cbom_files[0]).read_text(encoding="utf-8"))
                _update_scan(scan_id, raw_scan=raw_data, raw_html=_build_raw_html(raw_data))

            _update_scan(scan_id, status=SCAN_STATUS_DONE, finished_at=_now_iso())
            _append_output(scan_id, "Scan completed successfully")
        else:
            _update_scan(scan_id, status=SCAN_STATUS_FAILED, finished_at=_now_iso(),
                         error=f"VECTOR-Code exited with code {exit_code}")
            _append_output(scan_id, f"Scan failed (exit code {exit_code})")

    except Exception as exc:
        _update_scan(scan_id, status=SCAN_STATUS_FAILED, finished_at=_now_iso(),
                     error=str(exc))
        _append_output(scan_id, f"Unexpected error: {exc}")

def _run_network_scan(scan_id: str, protocol: str, target: str, port: int) -> None:
    _update_scan(scan_id, status=SCAN_STATUS_RUNNING)
    _append_output(scan_id, f"Starting VECTOR-Network scan: {target}:{port} ({protocol.upper()})")

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable, "-m", "tor.vector_network.main",
            "--protocol", protocol,
            "--target", target,
            "--port", str(port),
        ]

        proc = subprocess.Popen(
            cmd,
            cwd=str(VECTOR_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )

        for line in proc.stdout:
            _append_output(scan_id, line.rstrip("\n"))

        proc.wait()
        exit_code = proc.returncode
        _update_scan(scan_id, exit_code=exit_code)

        if exit_code == 0:
            if protocol == "tls":
                cbom_candidates = list(VECTOR_ROOT.glob("*_tls_cbom.json"))
                raw_candidates = list(VECTOR_ROOT.glob("*_tls_scan.json"))
            else:
                cbom_candidates = list(VECTOR_ROOT.glob("*_ssh_cbom.json"))
                raw_candidates = list(VECTOR_ROOT.glob("*_ssh_scan.json"))

            cbom_files = sorted(cbom_candidates, key=lambda p: p.stat().st_mtime, reverse=True)
            raw_files = sorted(raw_candidates,  key=lambda p: p.stat().st_mtime, reverse=True)

            raw_data = None
            if raw_files:
                try:
                    raw_data = json.loads(raw_files[0].read_text())
                except Exception:
                    pass

            cbom_paths = [str(p) for p in cbom_files]
            raw_html = _build_raw_html(raw_data) if raw_data else None
            _update_scan(scan_id, cbom_files=cbom_paths, raw_scan=raw_data, raw_html=raw_html)

            if cbom_paths:
                _score_cboms(scan_id, cbom_paths)
            else:
                _append_output(scan_id, "  Warning: no CBOM file found after scan")

            _update_scan(scan_id, status=SCAN_STATUS_DONE, finished_at=_now_iso())
            _append_output(scan_id, "Scan completed successfully")
        else:
            _update_scan(scan_id, status=SCAN_STATUS_FAILED, finished_at=_now_iso(),
                         error=f"VECTOR-Network exited with code {exit_code}")
            _append_output(scan_id, f"Scan failed (exit code {exit_code})")

    except Exception as exc:
        _update_scan(scan_id, status=SCAN_STATUS_FAILED, finished_at=_now_iso(),
                     error=str(exc))
        _append_output(scan_id, f"Unexpected error: {exc}")


@app.route("/")
def index():
    return render_template("new_scan.html")


@app.route("/new-scan")
def new_scan():
    return render_template("new_scan.html")


@app.route("/history")
def history():
    with _scans_lock:
        scans = list(_scans.values())
    scans.sort(key=lambda s: s["submitted_at"], reverse=True)
    return render_template("history.html", scans=scans)


@app.route("/results/<scan_id>")
def results(scan_id):
    scan = _get_scan(scan_id)
    if not scan:
        return render_template("error.html", message="Scan not found"), 404
    if scan.get("report_md") and not scan.get("report_html"):
        _update_scan(scan_id, report_html=_md_to_html(scan["report_md"]))
    if scan.get("scored_cbom") and not scan.get("cbom_html"):
        _update_scan(scan_id, cbom_html=_build_cbom_html(scan["scored_cbom"]))
    if scan.get("raw_scan") and not scan.get("raw_html"):
        _update_scan(scan_id, raw_html=_build_raw_html(scan["raw_scan"]))
    scan = _get_scan(scan_id)
    return render_template("results.html", scan=scan)


@app.route("/scan/<scan_id>")
def scan_detail(scan_id):
    scan = _get_scan(scan_id)
    if not scan:
        return render_template("error.html", message="Scan not found"), 404
    return render_template("scan_detail.html", scan=scan)


@app.route("/api/scan/code", methods=["POST"])
def api_scan_code():
    data     = request.get_json(force=True, silent=True) or {}
    source   = (data.get("source") or "").strip()
    app_name = (data.get("app_name") or "application").strip()

    if not source:
        return jsonify({"ok": False, "error": "Source path or GitHub URL is required"}), 400

    scan = _new_scan_record("code", source, app_name)
    with _scans_lock:
        _scans[scan["id"]] = scan

    threading.Thread(target=_run_code_scan, args=(scan["id"], source, app_name), daemon=True).start()
    return jsonify({"ok": True, "scan_id": scan["id"]}), 201


@app.route("/api/scan/network", methods=["POST"])
def api_scan_network():
    data = request.get_json(force=True, silent=True) or {}
    protocol = (data.get("protocol") or "").strip().lower()
    target = (data.get("target") or "").strip()
    port_raw = data.get("port")

    if protocol not in ("ssh", "tls"):
        return jsonify({"ok": False, "error": "Protocol must be 'ssh' or 'tls'"}), 400
    if not target:
        return jsonify({"ok": False, "error": "Target is required"}), 400
    try:
        port = int(port_raw)
        assert 1 <= port <= 65535
    except Exception:
        return jsonify({"ok": False, "error": "Port must be an integer between 1 and 65535"}), 400

    scan = _new_scan_record(f"network-{protocol}", f"{target}:{port}", f"{target}:{port}")
    with _scans_lock:
        _scans[scan["id"]] = scan

    threading.Thread(target=_run_network_scan, args=(scan["id"], protocol, target, port), daemon=True).start()
    return jsonify({"ok": True, "scan_id": scan["id"]}), 201


@app.route("/api/scan/<scan_id>")
def api_scan_status(scan_id):
    scan = _get_scan(scan_id)
    if not scan:
        return jsonify({"ok": False, "error": "Not found"}), 404

    since = request.args.get("since", type=int, default=0)
    with _scans_lock:
        lines = scan["output_lines"][since:]
        has_results = bool(scan.get("scored_cbom") or scan.get("cbom_files"))

    return jsonify({
        "ok": True,
        "id": scan_id,
        "status": scan["status"],
        "submitted_at": scan["submitted_at"],
        "finished_at": scan["finished_at"],
        "type": scan["type"],
        "target": scan["target"],
        "app_name": scan["app_name"],
        "output_lines": lines,
        "output_total": len(scan["output_lines"]),
        "error": scan.get("error"),
        "exit_code": scan.get("exit_code"),
        "has_results": has_results,
    })


@app.route("/api/scans")
def api_scans():
    with _scans_lock:
        scans = list(_scans.values())
    scans.sort(key=lambda s: s["submitted_at"], reverse=True)
    return jsonify([{
        "id": s["id"],
        "type": s["type"],
        "target": s["target"],
        "app_name": s["app_name"],
        "status": s["status"],
        "submitted_at": s["submitted_at"],
        "finished_at": s["finished_at"],
        "has_results": bool(s.get("scored_cbom") or s.get("cbom_files")),
    } for s in scans])


@app.route("/api/scan/<scan_id>/results")
def api_scan_results(scan_id):
    scan = _get_scan(scan_id)
    if not scan:
        return jsonify({"ok": False, "error": "Not found"}), 404
    if scan["status"] != SCAN_STATUS_DONE:
        return jsonify({"ok": False, "error": "Scan not complete"}), 400
    return jsonify({
        "ok": True,
        "scored_cbom": scan.get("scored_cbom"),
        "report_md": scan.get("report_md"),
        "raw_scan": scan.get("raw_scan"),
        "cbom_files": [Path(p).name for p in scan.get("cbom_files", [])],
    })


@app.route("/api/scan/<scan_id>/download/cbom")
def api_download_cbom(scan_id):
    scan = _get_scan(scan_id)
    if not scan or not scan.get("scored_cbom"):
        return jsonify({"ok": False, "error": "No CBOM available"}), 404
    return Response(
        json.dumps(scan["scored_cbom"], indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=cbom_{scan_id[:8]}_scored.json"}
    )


@app.route("/api/scan/<scan_id>/download/report")
def api_download_report(scan_id):
    scan = _get_scan(scan_id)
    if not scan or not scan.get("report_md"):
        return jsonify({"ok": False, "error": "No report available"}), 404
    return Response(
        scan["report_md"],
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=risk_report_{scan_id[:8]}.md"}
    )


@app.route("/api/scan/<scan_id>/stream")
def api_scan_stream(scan_id):
    def generate():
        sent = 0
        while True:
            scan = _get_scan(scan_id)
            if not scan:
                yield "event: error\ndata: Scan not found\n\n"
                return
            with _scans_lock:
                lines  = scan["output_lines"][sent:]
                status = scan["status"]
            for line in lines:
                yield f"data: {line.replace(chr(10), ' ')}\n\n"
                sent += 1
            if status in (SCAN_STATUS_DONE, SCAN_STATUS_FAILED):
                yield f"event: done\ndata: {status}\n\n"
                return
            time.sleep(0.5)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("VECTOR_PORT", 5000))
    print(f"VECTOR Web Interface running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)