"""Write the read-only part of the API as static files ("demo mode", contract section 'Principles' 2).

Usage: ENGINE_DATA=... ENGINE_STATE=... python -m engine.export_static OUT_DIR [scan_id ...] [--windows lung]
Produces OUT_DIR/api/v1/health.json, scans.json, scans/<id>/meta.json, findings.json, slices/<window>/<z>.png
Only processed scans are exported.
"""
import json, os, sys

from . import api


def main():
    args = sys.argv[1:]
    windows = ["lung"]
    if "--windows" in args:
        i = args.index("--windows"); windows = args[i + 1].split(","); args = args[:i] + args[i + 2:]
    out, ids = args[0], args[1:] or [s for s in api.all_ids() if api.processed(s)]
    base = f"{out}/api/v1"
    os.makedirs(base, exist_ok=True)
    h = api.health(); h.update(mode="static", refine_available=False)
    json.dump(h, open(f"{base}/health.json", "w"))
    rows = [api.scan_row(i) for i in ids]
    for r in rows:  # a prior that is not in the demo set cannot be referenced
        if r["prior_scan_id"] not in ids:
            r["prior_scan_id"] = None
    json.dump({"scans": rows}, open(f"{base}/scans.json", "w"))
    for sid in ids:
        d = f"{base}/scans/{sid}"
        os.makedirs(d, exist_ok=True)
        m = api.scan_meta(sid); m["windows"] = windows
        json.dump(m, open(f"{d}/meta.json", "w"))
        json.dump(api.findings(sid), open(f"{d}/findings.json", "w"))
        s = api.get_scan(sid)
        for w in windows:
            os.makedirs(f"{d}/slices/{w}", exist_ok=True)
            for z in range(s.n):
                open(f"{d}/slices/{w}/{z}.png", "wb").write(api.slice_png_bytes(s, z, w))
        print(sid, "exported", flush=True)


if __name__ == "__main__":
    main()
