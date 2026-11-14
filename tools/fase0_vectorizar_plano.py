"""Phase 0: vectorize the official 2022 zoning map PDF (raster) into georeferenced polygons.

The municipal GIS server is unreachable, so the zone polygons are rebuilt from
`plano-de-zonificacion.pdf` (1:25.000):
  1. Text and vector overlays are removed; the embedded raster is rendered at native resolution.
  2. Zone/radio boundaries (thick black lines) + fill-colour classes split the map into regions.
  3. Each zone label (vector text: "Rm1", "Rmb2", ...) is assigned to the nearby region whose
     colour matches the zone family (residential orange, commercial red, ...).
  4. Unlabelled regions inherit the zone of the nearest labelled region of the same colour.
  5. Pixel -> PDF point -> EPSG:5347 via an affine transform fitted against the partido outline
     from UrbaSIG (Provincia de Buenos Aires), then -> EPSG:4326.

Usage:
    python tools/fase0_vectorizar_plano.py <plano.pdf> <affine_T.npy>
Output:
    data/zonas_san_isidro.geojson  (zona, radio, asignacion, colour group)
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pyproj
from scipy import ndimage as ndi
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "zonas_san_isidro.geojson"
with open(ROOT / "data" / "fot_por_zona.csv", encoding="utf-8") as fh:
    FOT = {row["zona"]: float(row["fot"] or 0) for row in csv.DictReader(fh)}

PT_PER_PX = 0.2400298762751902          # native raster resolution inside the PDF
DARK_MAX = 100                          # zone boundary lines are near-black
MEDIAN = 5
MIN_REGION_PX = 1200                    # ~5.000 m2
LABEL_RADIUS_PX = 30                    # ~60 m search radius around a label
GREEN_OPEN_PX = 12                      # ~25 m: white/green strips thinner than 2x this are not zones

# Fill colours of the map (k-means centres, RGB) grouped into families.
PALETTE = {
    "orange": [(249, 215, 144), (236, 205, 137), (254, 217, 146)],
    "tan": [(219, 202, 169), (205, 183, 137), (178, 143, 125), (240, 221, 194)],
    "yellow": [(253, 253, 198)],
    "red": [(250, 145, 146), (225, 142, 142)],
    "purple": [(234, 199, 253)],
    "violet": [(202, 171, 219)],
    "grey_dark": [(170, 169, 170)],
    "grey_mid": [(207, 208, 207)],
    "grey_light": [(229, 230, 227)],
    "green_white": [(250, 251, 246), (217, 233, 202)],
    "dark": [(118, 116, 109)],
}
ZONE_FAMILY = [
    (r"^(Rm\d|Rmb\d|RmbB)$", {"orange"}),
    (r"^(Ra\d|Rma\d?C?)$", {"tan"}),
    (r"^(Rb\d|RbPN)$", {"yellow"}),
    (r"^(Ca1C?|Cma\d|Cm\d|Cmb\d|CmbB|Cb\d)$", {"red"}),
    (r"^(CE1|CR1)$", {"red", "tan"}),
    (r"^(ID|IN)$", {"purple"}),
    (r"^IE$", {"violet"}),
    (r"^APP1$", {"grey_dark"}),
    (r"^(APP2|AR|DUP1)$", {"grey_mid"}),
    (r"^Ru$", {"grey_light"}),
    (r"^(Ec|E|EH|EPR)$", {"green_white"}),
]
LABEL_RE = re.compile(
    r"^(Ra\d|Rma\d?C?|Rm\d|Rmb\d|RmbB|Rb\d|RbPN|APP\d|Ca1C?|Cma\d|Cm\d|Cmb\d|CmbB|Cb\d|"
    r"CE\d|CR\d|ID|IE|IN|Ec|EH|EPR|E|AR|Ru|DUP\d)$")


def family_of(zone):
    for pat, fam in ZONE_FAMILY:
        if re.match(pat, zone):
            return fam
    return set()


def render_raster(page):
    page.add_redact_annot(page.rect)
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                          graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                          text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    z = 1 / PT_PER_PX
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3).copy()


def read_labels(page):
    words = page.get_text("words")
    labels = []
    for x0, y0, x1, y1, text, *_ in words:
        if not LABEL_RE.match(text) or y1 > 790 or y0 < 80 or (x0 < 150 and y0 > 560):
            continue
        near = [w for w in words if y1 - 1 < w[1] < y1 + 9 and abs((w[0] + w[2]) / 2 - (x0 + x1) / 2) < 25]
        sub = " ".join(w[4] for w in sorted(near, key=lambda w: w[0]))
        m = re.search(r"(Radio|Sector)\s*(\w+)", sub)
        labels.append({"zona": text, "radio": f"{m.group(1)} {m.group(2)}" if m else "",
                       "x": (x0 + x1) / 2 / PT_PER_PX, "y": (y0 + y1) / 2 / PT_PER_PX})
    return labels


def partido_mask(raster):
    nw = (raster.min(axis=2) < 235).astype(np.uint8)
    frame = np.zeros_like(nw)
    frame[int(80 / PT_PER_PX):int(790 / PT_PER_PX), int(28 / PT_PER_PX):int(1165 / PT_PER_PX)] = 1
    m = cv2.morphologyEx(nw * frame, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    _, lab, st, _ = cv2.connectedComponentsWithStats(m)
    part = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
    part = cv2.morphologyEx(part, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    part[int(560 / PT_PER_PX):, :int(150 / PT_PER_PX)] = 0      # legend box
    return part > 0


def segment(raster, part):
    dark = (raster.max(axis=2) < DARK_MAX).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    dark = cv2.dilate(dark, np.ones((2, 2), np.uint8))
    med = cv2.medianBlur(raster, MEDIAN)
    names, centres = [], []
    for fam, cols in PALETTE.items():
        for c in cols:
            names.append(fam)
            centres.append(c)
    centres = np.array(centres, np.float32)
    fam_ids = {f: i for i, f in enumerate(PALETTE)}
    idx = np.empty(med.shape[:2], np.int32)
    for r0 in range(0, med.shape[0], 500):      # chunked to limit memory
        blk = med[r0:r0 + 500].reshape(-1, 1, 3).astype(np.float32)
        idx[r0:r0 + 500] = ((blk - centres[None]) ** 2).sum(-1).argmin(1).reshape(-1, med.shape[1])
    group = np.array([fam_ids[n] for n in names])[idx]
    group[(~part) | (dark > 0)] = -1
    reg = np.zeros(group.shape, np.int32)
    nxt = 1
    for v in np.unique(group[group >= 0]):
        lab, n = ndi.label(group == v)
        reg[lab > 0] = lab[lab > 0] + nxt - 1
        nxt += n
    sizes = np.bincount(reg.ravel())
    big = sizes >= MIN_REGION_PX
    big[0] = False
    keep = np.where(big[reg], reg, 0)
    _, (iy, ix) = ndi.distance_transform_edt(keep == 0, return_indices=True)
    full = keep[iy, ix]
    full[~part] = 0
    # colour family of each region = majority family of its own (non-filled) pixels
    fam_names = list(PALETTE)
    reg_family = {}
    for r in np.unique(keep[keep > 0]):
        vals = group[keep == r]
        reg_family[int(r)] = fam_names[Counter(vals[vals >= 0].tolist()).most_common(1)[0][0]]
    return full, reg_family


def assign(full, reg_family, labels):
    h, w = full.shape
    yy, xx = np.ogrid[-LABEL_RADIUS_PX:LABEL_RADIUS_PX + 1, -LABEL_RADIUS_PX:LABEL_RADIUS_PX + 1]
    disk = xx ** 2 + yy ** 2 <= LABEL_RADIUS_PX ** 2
    votes = defaultdict(list)            # region -> [(zona, radio, weight, how)]
    for l in labels:
        x, y = int(l["x"]), int(l["y"])
        win = full[max(0, y - LABEL_RADIUS_PX):y + LABEL_RADIUS_PX + 1, max(0, x - LABEL_RADIUS_PX):x + LABEL_RADIUS_PX + 1]
        d = disk[:win.shape[0], :win.shape[1]]
        cnt = Counter(win[d & (win > 0)].tolist())
        fam = family_of(l["zona"])
        ok = [(r, c) for r, c in cnt.items() if reg_family.get(r) in fam]
        if ok:
            r, c = max(ok, key=lambda t: t[1])
            votes[r].append((l["zona"], l["radio"], c, "etiqueta"))
        else:
            r = int(full[y, x])
            if r:
                votes[r].append((l["zona"], l["radio"], 1, "etiqueta_sin_color"))
    zone_of = {}
    for r, v in votes.items():
        # on conflicting labels prefer the highest FOT: a missed opportunity costs more than a false hit
        best = max(v, key=lambda t: (FOT.get(t[0], 0), t[2]))
        conflict = len({t[0] for t in v}) > 1
        zone_of[r] = (best[0], best[1], best[3] + ("_conflicto" if conflict else ""))
    # unlabelled regions: nearest labelled region of the same colour family
    for fam in set(reg_family.values()):
        seeds = np.isin(full, [r for r in zone_of if reg_family.get(r) == fam])
        todo = [r for r, f in reg_family.items() if f == fam and r not in zone_of]
        if not todo or not seeds.any():
            continue
        _, (iy, ix) = ndi.distance_transform_edt(~seeds, return_indices=True)
        for r in todo:
            ys, xs = np.nonzero(full == r)
            src = Counter(full[iy[ys, xs], ix[ys, xs]].tolist()).most_common(1)[0][0]
            z = zone_of[src]
            zone_of[r] = (z[0], z[1], "inferida_vecino")
    return zone_of


def to_polygons(full, zone_of, reg_family, T):
    tr = pyproj.Transformer.from_crs(5347, 4326, always_xy=True).transform

    def px_to_m(x, y):
        xp, yp = x * PT_PER_PX, -(y * PT_PER_PX)
        return T[0, 0] * xp + T[0, 1] * yp + T[0, 2], T[1, 0] * xp + T[1, 1] * yp + T[1, 2]

    groups = defaultdict(list)
    for r, (zona, radio, how) in zone_of.items():
        groups[(zona, radio, how, reg_family.get(r, ""))].append(r)
    feats = []
    for (zona, radio, how, fam), regs in groups.items():
        mask = np.isin(full, regs).astype(np.uint8)
        if fam == "green_white":
            # roads, railways and the partido edge are drawn white too: drop strips thinner than ~50 m
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * GREEN_OPEN_PX + 1,) * 2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
        cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        polys = []
        for i, c in enumerate(cnts):
            if hier[0][i][3] != -1 or len(c) < 3:
                continue
            holes = [cnts[j][:, 0, :] for j in range(len(cnts)) if hier[0][j][3] == i and len(cnts[j]) >= 3]
            p = Polygon(c[:, 0, :], holes).buffer(0)
            if p.area > 50:
                polys.append(p)
        if not polys:
            continue
        g = unary_union(polys)
        g = transform(lambda x, y: px_to_m(np.asarray(x), np.asarray(y)), g).simplify(2).buffer(0)
        g = transform(tr, g)
        feats.append({"type": "Feature", "geometry": mapping(g),
                      "properties": {"zona": zona, "radio": radio, "asignacion": how, "color": fam}})
    return {"type": "FeatureCollection", "features": feats}


def main():
    pdf, t_path = sys.argv[1], sys.argv[2]
    T = np.load(t_path)
    page = pymupdf.open(pdf)[0]
    labels = read_labels(page)
    raster = render_raster(pymupdf.open(pdf)[0])
    part = partido_mask(raster)
    full, reg_family = segment(raster, part)
    zone_of = assign(full, reg_family, labels)
    fc = to_polygons(full, zone_of, reg_family, T)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    how = Counter(f["properties"]["asignacion"] for f in fc["features"])
    print(f"labels {len(labels)}, regions {len(zone_of)}, features {len(fc['features'])}, {dict(how)}")
    np.save(ROOT / "data" / "_debug_regions.npy", full) if "--debug" in sys.argv else None


if __name__ == "__main__":
    main()
