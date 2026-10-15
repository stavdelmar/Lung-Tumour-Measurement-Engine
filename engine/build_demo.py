"""Build the engine state + static demo folder from Colab's AI cache (no model run needed).

Usage: python -m engine.build_demo NII_DIR CACHE_DIR STATE_DIR DEMO_OUT PATIENT [PATIENT ...]
  NII_DIR   <PID>_<TEST|RETEST>_ct.nii.gz + _meta.json (engine/prepare_data.py)
  CACHE_DIR <PID>_<TEST|RETEST>.npz from the Colab exam (lobes, nod, prob)
Writes STATE_DIR (for the live API) and DEMO_OUT/api/v1/... (static demo mode, lung window).
"""
import os, shutil, sys

if __name__ == "__main__":
    nii, cache, state, out = sys.argv[1:5]
    patients = sys.argv[5:]
    os.makedirs(state, exist_ok=True)
    os.environ["ENGINE_DATA"], os.environ["ENGINE_STATE"] = nii, state
    for pid in patients:  # the API reads its AI cache as <fid>_ai.npz
        for tp in ("TEST", "RETEST"):
            src = f"{cache}/{pid}_{tp}.npz"
            if os.path.exists(src):
                shutil.copy(src, f"{state}/{pid}_{tp}_ai.npz")
    from . import api, export_static
    ids = []
    for pid in patients:
        for tp in ("test", "retest"):
            sid = f"{pid}_{tp}"
            if os.path.exists(f"{state}/{api.file_id(sid)}_ai.npz"):
                api.process_scan(sid, force=True)  # uses the cached AI output: measure + match only
                ids.append(sid)
                f = api.findings(sid)
                print(sid, len(f["findings"]), "findings:",
                      [(x["finding_id"], x["lobe"], x["long_axis_mm"], x["type_guess"],
                        (x["match"] or {}).get("prior_finding_id")) for x in f["findings"]], flush=True)
    sys.argv = ["export_static", out] + ids
    export_static.main()
