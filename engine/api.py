"""Engine HTTP API (FastAPI) — contract v1: claude/engine-api-contract.md (project) / docs/engine_api.md.
Research use only.

Every read is a GET of a .json/.png path, so `engine.export_static` can write the same tree as static
files ("demo mode"). The only live call is POST /refine.

Run:  ENGINE_DATA=/data/scans ENGINE_STATE=/data/state uvicorn engine.api:app --port 7860
ENGINE_DATA holds <PID>_<TEST|RETEST>_ct.nii.gz + _meta.json (engine/prepare_data.py).

Coordinates in the API: z = 0 is the most superior slice; x = column, y = row of the PNG (= voxel grid).
Inside the engine arrays are SimpleITK (k, row, col) with k = 0 usually the most INFERIOR slice;
`Scan.z_api(k)` converts.
"""
import io, json, os, threading, queue, time, traceback
from datetime import datetime, timezone
import numpy as np
import SimpleITK as sitk
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from . import measure, match, correct
from .pipeline import run_scan, ENGINE_VERSION

DATA = os.environ.get("ENGINE_DATA", "data/scans")
STATE = os.environ.get("ENGINE_STATE", "data/state")
os.makedirs(STATE, exist_ok=True)
TIMEPOINT = {"TEST": "Baseline", "RETEST": "Follow-up 1"}
WINDOWS = {"lung": (-600, 1500), "mediastinal": (40, 350)}  # level, width
LOW_CONF = 0.6  # mean model probability inside the outline (see measure.components)
FAINT_RIM_MM = 4.0  # outline would be >= this much longer if the image chose the halo width (outline.faint_rim_growth)

app = FastAPI(title="Lung nodule engine", version=ENGINE_VERSION, description="Research use only.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class EngineError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


@app.exception_handler(EngineError)
def _err(_, e):
    return JSONResponse(status_code=e.status, content={"error": {"code": e.code, "message": e.message}})


# ---------------------------------------------------------------- ids and scans
def file_id(scan_id):            # "RIDER-1_retest" -> "RIDER-1_RETEST"
    pid, tp = scan_id.rsplit("_", 1)
    return f"{pid}_{tp.upper()}"


def api_id(fid):
    pid, tp = fid.rsplit("_", 1)
    return f"{pid}_{tp.lower()}"


def all_ids():
    return sorted(api_id(f[:-10]) for f in os.listdir(DATA) if f.endswith("_meta.json"))


def meta(scan_id):
    f = f"{DATA}/{file_id(scan_id)}_meta.json"
    if not os.path.exists(f):
        raise EngineError(404, "unknown_scan", scan_id)
    return json.load(open(f))


def prior_of(scan_id):
    pid, tp = scan_id.rsplit("_", 1)
    p = f"{pid}_test"
    return p if tp == "retest" and os.path.exists(f"{DATA}/{file_id(p)}_meta.json") else None


class Scan:
    """One scan in memory (only one or two kept: free machines are small)."""
    def __init__(self, scan_id):
        self.id = scan_id
        self.fid = file_id(scan_id)
        self.meta = meta(scan_id)
        self.img = sitk.ReadImage(f"{DATA}/{self.fid}_ct.nii.gz")
        self.hu = sitk.GetArrayFromImage(self.img)
        self.sp = tuple(np.array(self.img.GetSpacing())[::-1])
        d = np.array(self.img.GetDirection()).reshape(3, 3)
        self.flip = d[2, 2] > 0  # index grows toward the head -> API z must be reversed
        self.n = self.hu.shape[0]
        self._ai = None

    def z_api(self, k):
        return int(self.n - 1 - k) if self.flip else int(k)

    k_from_api = z_api  # the mapping is its own inverse

    @property
    def ai(self):
        if self._ai is None:
            z = np.load(f"{STATE}/{self.fid}_ai.npz")
            self._ai = dict(prob=z["prob"], lobes=z["lobes"],
                            labels=np.load(f"{STATE}/{self.fid}_labels.npz")["labels"])
        return self._ai


_scans, _lock = {}, threading.RLock()


def get_scan(scan_id):
    with _lock:
        if scan_id not in _scans:
            if len(_scans) >= 2:
                _scans.pop(next(iter(_scans)))
            _scans[scan_id] = Scan(scan_id)
        return _scans[scan_id]


def processed(scan_id):
    return os.path.exists(f"{STATE}/{file_id(scan_id)}_findings.json")


def scan_row(scan_id):
    m = meta(scan_id)
    d = m.get("study_date", "")
    row = dict(scan_id=scan_id, patient_id=m["patient"],
               scan_date=f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d,
               timepoint=TIMEPOINT.get(m["scan"], m["scan"]), series_number=m.get("series_number"),
               slice_thickness_mm=m.get("slice_thickness"), n_slices=m["size"][2],
               rows=m["size"][1], cols=m["size"][0],
               pixel_spacing_mm=[round(m["spacing"][1], 4), round(m["spacing"][0], 4)],
               prior_scan_id=prior_of(scan_id))
    if processed(scan_id):
        f = json.load(open(f"{STATE}/{file_id(scan_id)}_findings.json"))
        row.update(status="processed", n_findings=len(f["findings"]), processed_at=f["generated_at"])
    else:
        st = _jobs_status.get(scan_id, "new")
        row.update(status=st, n_findings=None, processed_at=None)
        if st == "failed":
            row["error"] = _jobs_error.get(scan_id)
    return row


# ---------------------------------------------------------------- findings format
def to_finding(n, s, labels_k, prior=None):
    """Engine nodule dict -> contract Finding (PNG pixel coords, API z)."""
    from skimage import measure as skm
    flip = lambda p: [round(float(p[1]), 1), round(float(p[0]), 1)]  # (row, col) -> [x, y]
    cz, cy, cx = n["center_voxel"]
    (z0, z1), (y0, y1), (x0, x1) = n["bbox"]
    za, zb = sorted([s.z_api(z0), s.z_api(z1 - 1)])
    contours = {}
    for k in range(z0, z1):
        sl = labels_k[k - z0] if labels_k is not None else None
        if sl is None or not sl.any():
            continue
        rings = []
        for ring in skm.find_contours(np.pad(sl, 1).astype(float), 0.5):
            ring = skm.approximate_polygon(ring - 1 + [y0, x0], tolerance=0.5)
            if len(ring) > 60:
                ring = ring[np.linspace(0, len(ring) - 1, 60).astype(int)]
            rings.append([flip(p) for p in ring])
        contours[str(s.z_api(k))] = rings
    flags = []
    if n.get("confidence") is not None and n["confidence"] < LOW_CONF:
        flags.append("low_confidence")
    # small model core inside a fainter, larger-looking opacity: the outline may be too SMALL (17 Oct)
    if (n.get("faint_rim_growth_mm") or 0) >= FAINT_RIM_MM:
        flags.append("faint_rim")
        if "low_confidence" not in flags:
            flags.append("low_confidence")
    if n["long_axis_mm"] < 4:
        flags.append("below_4mm")
    if n.get("touches_pleura"):
        flags.append("touches_pleura")
    # vessel seen end-on: thin and long in z compared with its in-plane size
    if n["n_slices"] * s.sp[0] > 2.5 * max(n["long_axis_mm"], 1) and n["long_axis_mm"] < 10:
        flags.append("possible_vessel")
    return dict(
        finding_id=n["nodule_id"].replace("N", "F"), source=n.get("source", "ai"),
        confidence=n.get("confidence"), detection_max_prob=n.get("detection_max_prob"),
        type_guess=n["type"], lobe=n["lobe"],
        key_slice_z=s.z_api(n["slice_index"]), key_slice_number=n["slice_number"],
        centroid_zyx=[round((s.n - 1 - cz) if s.flip else cz, 1), cy, cx],
        bbox_zyx=[[za, y0, x0], [zb, y1 - 1, x1 - 1]],
        long_axis_mm=n["long_axis_mm"], short_axis_mm=n["short_axis_mm"],
        mean_diameter_mm=n["mean_diameter_mm"],
        solid_component_mm=n.get("solid_component_mm"),
        long_axis_px=[flip(p) for p in n["long_axis_px"]] if n.get("long_axis_px") else None,
        short_axis_px=[flip(p) for p in n["short_axis_px"]] if n.get("short_axis_px") else None,
        volume_mm3=n["volume_mm3"], mean_hu=n.get("mean_hu"), n_slices=n["n_slices"],
        faint_rim_growth_mm=n.get("faint_rim_growth_mm"),
        contours=contours, match=None, flags=flags)


def build_findings(s, nodules, labels):
    out = []
    for i, n in enumerate(nodules):
        (z0, z1), (y0, y1), (x0, x1) = n["bbox"]
        out.append(to_finding(n, s, labels[z0:z1, y0:y1, x0:x1] == i + 1))
    return out


def save_findings(s, nodules, labels, match_info=None, generated_at=None):
    findings = build_findings(s, nodules, labels)
    if match_info:
        prior = match_info["prior_scan_id"]
        for f in findings:
            p = next((p for p in match_info["pairs"] if p["current"] == f["finding_id"]), None)
            if p:
                f["match"] = dict(prior_scan_id=prior, prior_finding_id=p["prior"], distance_mm=p["distance_mm"],
                                  confidence=p.get("confidence"), set_by=p.get("set_by", "engine"))
    doc = dict(scan_id=s.id, engine_version=ENGINE_VERSION,
               generated_at=generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               research_use_only=True, findings=findings,
               match_summary=None if not match_info else {k: v for k, v in match_info.items() if k != "pairs"})
    json.dump(doc, open(f"{STATE}/{s.fid}_findings.json", "w"))
    json.dump(dict(nodules=nodules, match=match_info), open(f"{STATE}/{s.fid}_nodules.json", "w"))
    np.savez_compressed(f"{STATE}/{s.fid}_labels.npz", labels=labels)
    if s._ai is not None:
        s._ai["labels"] = labels
    return doc


def load_nodules(s):
    d = json.load(open(f"{STATE}/{s.fid}_nodules.json"))
    return d["nodules"], d.get("match")


# ---------------------------------------------------------------- batch processing
_jobs, _jobs_status, _jobs_error = queue.Queue(), {}, {}


def process_scan(scan_id, force=False):
    """Run the full AI draft for one scan (and its prior first, if any). Blocking."""
    prior = prior_of(scan_id)
    if prior and not processed(prior):
        process_scan(prior)
    if processed(scan_id) and not force:
        return
    s = get_scan(scan_id)
    nodules, labels, lobes, prob, tim = run_scan(f"{DATA}/{s.fid}_ct.nii.gz", s.meta,
                                                 cache_npz=f"{STATE}/{s.fid}_ai.npz")
    for n in nodules:
        n["nodule_id"] = n["nodule_id"].replace("N", "F")
    mi = None
    if prior:
        mi = rematch(s, nodules, lobes)
    save_findings(s, nodules, labels, mi)
    json.dump(tim, open(f"{STATE}/{s.fid}_timings.json", "w"))


_tx = {}


def transform_to_prior(s, lobes=None):
    f = f"{STATE}/{s.fid}_to_prior.tfm"
    if s.id not in _tx:
        if os.path.exists(f):
            _tx[s.id] = sitk.ReadTransform(f)
        else:
            p = get_scan(prior_of(s.id))
            lobes = lobes if lobes is not None else s.ai["lobes"]
            tx, _ = match.register(s.img, p.img, lobes, p.ai["lobes"])
            sitk.WriteTransform(tx, f)
            _tx[s.id] = tx
    return _tx[s.id]


def rematch(s, nodules, lobes=None):
    prior = prior_of(s.id)
    p = get_scan(prior)
    pn, _ = load_nodules(p)
    tx = transform_to_prior(s, lobes)
    m = match.match(nodules, pn, tx, s.img, p.img)
    for pr in m["pairs"]:  # simple confidence: 1 at 0 mm, 0 at the gate
        pr["confidence"] = round(max(0.0, 1 - pr["distance_mm"] / 15.0), 2)
    m["prior_scan_id"] = prior
    return m


def _worker():
    while True:
        sid = _jobs.get()
        try:
            _jobs_status[sid] = "processing"
            process_scan(sid, force=True)
            _jobs_status.pop(sid, None)
        except Exception as e:
            traceback.print_exc()
            _jobs_status[sid], _jobs_error[sid] = "failed", str(e)


threading.Thread(target=_worker, daemon=True).start()


# ---------------------------------------------------------------- read endpoints
@app.get("/api/v1/health.json")
def health():
    return dict(status="ok", engine_version=ENGINE_VERSION, mode="live", research_use_only=True,
                models=dict(detector="TotalSegmentator lung_nodules (nnU-Net, BlueMind AI)",
                            lobes="TotalSegmentator total 3mm", segmenter="same as detector + click-to-correct"),
                refine_available=True)


@app.get("/api/v1/scans.json")
def scans():
    return {"scans": [scan_row(i) for i in all_ids()]}


@app.get("/api/v1/scans/{scan_id}/meta.json")
def scan_meta(scan_id: str):
    row = scan_row(scan_id)
    m = meta(scan_id)
    n = m["size"][2]
    s = get_scan(scan_id)
    zpos = [s.img.TransformIndexToPhysicalPoint((0, 0, k))[2] for k in range(n)]
    sl = [None] * n
    for k in range(n):
        sl[s.z_api(k)] = dict(z=s.z_api(k), slice_number=int(m["instance_numbers"][k]), z_position_mm=round(zpos[k], 2))
    row.update(slices=sl, windows=list(WINDOWS))
    return row


def slice_png_bytes(s, z, window):
    from PIL import Image
    if window not in WINDOWS:
        raise EngineError(404, "unknown_window", window)
    if not 0 <= z < s.n:
        raise EngineError(404, "bad_slice", str(z))
    L, W = WINDOWS[window]
    a = s.hu[s.k_from_api(z)].astype(np.float32)
    a = np.clip((a - (L - W / 2)) / W * 255, 0, 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(a).save(buf, "PNG", optimize=True)
    return buf.getvalue()


@app.get("/api/v1/scans/{scan_id}/slices/{window}/{z}.png")
def slice_png(scan_id: str, window: str, z: int):
    return Response(slice_png_bytes(get_scan(scan_id), z, window), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=31536000"})


@app.get("/api/v1/scans/{scan_id}/findings.json")
def findings(scan_id: str):
    meta(scan_id)
    if not processed(scan_id):
        raise EngineError(409, "not_processed", f"status: {_jobs_status.get(scan_id, 'new')}")
    return json.load(open(f"{STATE}/{file_id(scan_id)}_findings.json"))


# ---------------------------------------------------------------- live endpoints
@app.post("/api/v1/scans/{scan_id}/process")
def process(scan_id: str, body: dict = Body(default={})):
    meta(scan_id)
    if processed(scan_id) and not body.get("force"):
        return {"status": "processed"}
    if _jobs_status.get(scan_id) not in ("queued", "processing"):
        _jobs_status[scan_id] = "queued"
        _jobs.put(scan_id)
    return {"status": _jobs_status[scan_id]}


@app.post("/api/v1/scans/{scan_id}/refine")
def refine(scan_id: str, body: dict = Body(...)):
    """Daniel fixes a finding with clicks / a box / a redrawn polygon on slice z, or adds a missed one."""
    t0 = time.time()
    s = get_scan(scan_id)
    if not processed(scan_id):
        raise EngineError(409, "not_processed", "process the scan first")
    nodules, mi = load_nodules(s)
    labels = s.ai["labels"].copy()
    k = s.k_from_api(int(body["z"]))
    pts = [(k, float(p["y"]), float(p["x"]), int(p.get("label", 1))) for p in body.get("points", [])]
    pos = [p[:3] for p in pts if p[3] == 1]
    neg = [p[:3] for p in pts if p[3] == 0]
    if body.get("box_px") and not pos:  # box only: use its centre as the positive click
        x0, y0, x1, y1 = body["box_px"]
        pos = [(k, (y0 + y1) / 2, (x0 + x1) / 2)]
    fid = body.get("finding_id")
    if fid is None:  # add a missed nodule
        if not pos and not body.get("polygon_px"):
            raise EngineError(422, "no_prompt", "give at least one positive point, a box or a polygon")
        if pos:
            m, how = correct.region_at(pos[0], s.ai["prob"], s.hu, s.ai["lobes"], s.sp)
            for p in pos[1:]:
                m = correct.grow(m, [p], s.ai["prob"], s.hu, s.ai["lobes"], s.sp)
        else:
            m, how = np.zeros(labels.shape, bool), "polygon"
        if body.get("box_px"):
            m = _clip_box(m, k, body["box_px"])
        ids = [int(n["nodule_id"][1:]) for n in nodules] or [0]
        nodules.append(dict(nodule_id=f"F{max(ids) + 1}", confidence=None, source="user_click"))
        i = len(nodules) - 1
    else:
        i = next((j for j, n in enumerate(nodules) if n["nodule_id"] == fid), None)
        if i is None:
            raise EngineError(404, "unknown_finding", fid)
        m = labels == i + 1
        how = "edit"
        m = correct.grow(m, pos, s.ai["prob"], s.hu, s.ai["lobes"], s.sp)
        m = correct.shrink(m, neg, s.sp)
        if body.get("box_px"):
            m = _clip_box(m, k, body["box_px"])
    if body.get("polygon_px"):
        m = correct.replace_slice(m, k, [[p[1], p[0]] for p in body["polygon_px"]])
    if not m.any():
        if fid is None:
            raise EngineError(404, "nothing_found", "no nodule found at this spot; draw its outline instead")
        raise EngineError(422, "empty_outline", "the correction removed the whole outline")
    labels[labels == i + 1] = 0
    labels[m & (labels == 0)] = i + 1
    mm = labels == i + 1
    n = measure.measure_nodule(mm, s.hu, s.sp, s.ai["lobes"], s.meta["instance_numbers"])
    zs, ys, xs = np.nonzero(mm)
    old = nodules[i]
    n.update(nodule_id=old["nodule_id"], source=old.get("source", "ai"), confidence=old.get("confidence"),
             bbox=[[int(zs.min()), int(zs.max()) + 1], [int(ys.min()), int(ys.max()) + 1], [int(xs.min()), int(xs.max()) + 1]])
    nodules[i] = n
    if prior_of(scan_id):
        mi = rematch(s, nodules)
    doc = save_findings(s, nodules, labels, mi)
    f = next(f for f in doc["findings"] if f["finding_id"] == n["nodule_id"])
    f["refine"] = dict(method=how, seconds=round(time.time() - t0, 1))
    return f


def _clip_box(m, k, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    out = m.copy()
    keep = np.zeros(m.shape[1:], bool); keep[max(y0, 0):y1 + 1, max(x0, 0):x1 + 1] = True
    out[k] &= keep
    return out
