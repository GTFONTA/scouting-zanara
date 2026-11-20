"""Multi-municipio: config overlays, the zones engine with Tigre / San Fernando data, and the CABA engine with
recorded Ciudad 3D answers (no network)."""

import copy
import csv
import gzip
import json

import pytest
import requests
from shapely.geometry import shape

from src import motor_caba
from src.config import load_config, municipios
from tests import harness


def test_municipios_listed():
    assert {"san_isidro", "caba", "tigre", "san_fernando"} <= set(municipios())


def test_san_isidro_is_the_base_config():
    cfg = load_config()
    assert cfg["municipio"]["slug"] == "san_isidro" and cfg["municipio"]["motor"] == "zonas"
    assert cfg["productos"]["normativa_csv"] == "data/normativa_zonas.csv"
    assert not cfg["municipio"]["en_prueba"]


@pytest.mark.parametrize("slug", ["tigre", "san_fernando"])
def test_pba_overlay(slug):
    cfg = load_config(slug)
    assert cfg["municipio"]["en_prueba"]
    assert cfg["productos"]["normativa_csv"].startswith(f"municipios/{slug}/")
    assert cfg["productos"]["alias_zonas"] == {}                       # '!' replaced San Isidro's aliases
    assert "la horqueta" not in cfg["geocodificacion"]["alias_barrios"]
    assert all(slug.replace("_", "-") in u for u in cfg["portales"]["zonaprop"]["start_urls"])
    assert cfg["criterio"]["incidencia_max_usd"] == 350                 # Gonzalo, 14/11/2026


def _zonaprop_items(points):
    raw = json.loads(gzip.decompress((harness.GOLDEN / "2026-11-09_1851" / "raw_zonaprop.json.gz").read_bytes()))
    tpl = next(x for x in raw if (x.get("realEstateType") or {}).get("name") == "Terrenos")
    items = []
    for i, (lat, lon, s, price) in enumerate(points):
        it = copy.deepcopy(tpl)
        it["postingId"], it["title"] = f"P{i}", f"Lote prueba {i}"
        it["postingLocation"]["postingGeolocation"]["geolocation"] = {"latitude": lat, "longitude": lon}
        it["postingLocation"]["address"]["visibility"] = "EXACT"
        it["mainFeatures"]["CFT100"]["value"] = str(s)
        it["priceOperationTypes"][0]["prices"][0].update(amount=price, currency="USD")
        items.append(it)
    return items


def _point_in_zone(slug, zone):
    fc = json.loads((harness.GOLDEN.parent.parent / "municipios" / slug / "zonas.geojson").read_text(encoding="utf-8"))
    g = max((shape(f["geometry"]) for f in fc["features"] if f["properties"]["zona"] == zone), key=lambda g: g.area)
    c = g.representative_point()
    return c.y, c.x


def test_tigre_central_zone_is_a_multifamiliar_hit(monkeypatch, tmp_path):
    harness.offline(monkeypatch, tmp_path)
    from src import main
    cfg = load_config("tigre")
    cfg["productos"]["catastro"]["max_consultas_por_corrida"] = 0
    lat, lon = _point_in_zone("tigre", "C2a")
    rows, _ = main.process({"zonaprop": _zonaprop_items([(lat, lon, 1200, 600000), (lat, lon + 0.5, 1200, 600000)])},
                           cfg, [], [])
    hit, outside = rows
    assert hit["resultado"] == "oportunidad" and "multifamiliar" in hit["via"]
    assert hit["fot_usado"] == 4.5 and hit["m2_construibles"] == 5400      # premio Art. 47: 1.200 >= 2 x 300 m2
    assert "premio_ley_8912_aplicado" in hit["flags"]
    assert hit["requiere_cloaca"] and "requiere_cloaca_para_max" in hit["flags"]    # C1-C4: Gonzalo, 14/11
    assert "requiere_cloaca_multifamiliar" not in hit["flags"]
    assert outside["motivo_descarte"] == "fuera_del_partido"
    small = main.process({"zonaprop": _zonaprop_items([(lat, lon, 500, 300000)])}, cfg, [], [])[0][0]
    assert small["fot_usado"] == 3.0 and "premio_ley_8912_aplicado" not in small["flags"]   # 500 < 2 parcelas


def _normativa(slug):
    path = harness.GOLDEN.parent.parent / "municipios" / slug / "normativa_zonas.csv"
    with open(path, encoding="utf-8") as fh:
        return {row["zona"]: row for row in csv.DictReader(fh)}


def test_multifamiliar_decisions_of_gonzalo():
    """Zones checked by Gonzalo in each code (14/11/2026)."""
    from src.evaluate import multifamiliar, units
    tigre, sf = _normativa("tigre"), _normativa("san_fernando")
    p = load_config("tigre")["productos"]
    assert all("requiere_cloaca_multifamiliar" in tigre[z]["flags"] for z in ("C1", "C2a", "C2b", "C3", "C4a", "C4c"))
    assert "requiere_cloaca" not in tigre["C5"]["flags"]
    assert multifamiliar(tigre["R4"], 999, p) == "No" and multifamiliar(tigre["R4"], 1000, p) == "Sí"
    assert units(tigre["R4"], 800, None, p)["multifamiliar_unidades"] is None
    assert units(tigre["R4"], 2000, None, p)["multifamiliar_unidades"] == 7          # 140 hab/ha x 0,2 ha / 4
    assert {sf[z]["multifamiliar"] for z in ("C3", "C3A")} == {"Sí"}
    assert {sf[z]["multifamiliar"] for z in ("R3", "R3A", "R3B", "R4")} == {"No"}


# ---------------------------------------------------------------- CABA (recorded answers of 14/11/2026)

PARCEL = {"smp": "039-087-007", "direccion": "MOLDES 2477", "superficie_total": "617.00", "frente": "13.93"}
BUILDABLE = {"sup_max_edificable": 0, "sup_edificable_planta": 613.79, "altura_max": [31.2, 0, 0, 0],
             "altura_max_plano_limite": 38.0, "plusvalia": {"incidencia_uva": 420.0, "alicuota": 0.35, "distrito_cpu": "C2"},
             "fot": {"fot_medianera": 5.0, "fot_perim_libre": 7.0, "fot_semi_libre": 5.0},
             "parcelas_linderas": {"aph_linderas": False, "smp_linderas": ["039-087-006", "039-087-008"]},
             "catalogacion": {"proteccion": None},
             "distrito_especial": [], "tipica": "T", "afectaciones": {"riesgo_hidrico": 1}, "superficie_parcela": 613.8}
PLUS = {"plusvalia_em": 111925.8, "plusvalia_pl": 0, "plusvalia_sl": 111925.8, "incidencia_uva": 420.0}
UVA = {"results": [{"detalle": [{"fecha": "2026-11-14", "valor": 2196.12}]}]}
NEIGHBOURS = {"039-087-006": {"smp": "039-087-006", "pisos_sobre_rasante": "12"},      # taller than C.M. 31,2 m
              "039-087-008": {"smp": "039-087-008", "pisos_sobre_rasante": "2"}}


class FakeResp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


@pytest.fixture
def caba(monkeypatch, tmp_path):
    def get(self, url, params=None, **kw):
        if "catastro/parcela" in url and "smp" in params:
            return FakeResp(NEIGHBOURS.get(params["smp"], {}))
        if "catastro/parcela" in url:
            return FakeResp(PARCEL if params["lat"] < -34.5 else {})
        if "seccion_edificabilidad" in url:
            return FakeResp(BUILDABLE)
        if "calcular_plusvalia" in url:
            return FakeResp(PLUS)
        if "bcra" in url:
            return FakeResp(UVA)
        raise requests.ConnectionError(url)
    monkeypatch.setattr(requests.Session, "get", get)
    monkeypatch.setattr(motor_caba.time, "sleep", lambda s: None)
    monkeypatch.setattr(motor_caba, "dolar_mep", lambda ncfg: {"venta": 1580.9})
    cfg = load_config("caba")
    cfg["caba"]["cache"] = str(tmp_path / "cache_caba.json")
    return cfg


def test_caba_hit_with_plusvalia(caba):
    health = []
    rows = motor_caba.process({"zonaprop": _zonaprop_items([(-34.5600, -58.4620, 617, 1500000)])}, caba, health)
    r = rows[0]
    assert r["smp"] == "039-087-007" and r["parcela_coincide"]
    # the FOT only sets the plusvalía: entre medianeras (5), not the 7 of perímetro libre
    assert r["fot_usado"] == 5.0 and r["tipo_fot"] == "medianera"
    # C.M. 31,2 m: PB+9 at 2,90 m + 2 set-backs (44 m deep: 2 m and 8 m shorter) + basamento; 13,93 m front -> 0,75
    plan, net = 613.79, 613.79 * 0.75
    m2 = net * 10 + net * ((plan / 13.93 - 2) + (plan / 13.93 - 8)) / (plan / 13.93) + (617 - plan) * 0.75 * 2
    assert r["pisos"] == "PB+9 + 2 retiros + basamento" and r["eficiencia_planta"] == 0.75
    assert r["m2_construibles"] == round(m2)
    plus_uva = (0.8 * m2 - 5.0 * 617) * 420.0 * 0.35                    # Ley 6062 / 6710: 80% of the m2
    assert r["plusvalia_uva"] == round(plus_uva) and r["m2_sin_plusvalia"] == round(5.0 * 617 / 0.8)
    assert r["plusvalia_usd"] == round(plus_uva * 2196.12 / 1580.9)
    assert r["incidencia_total_usd_m2"] > r["incidencia_usd_m2"]
    assert r["resultado"] == "oportunidad" and r["ratio_incidencia"] <= 0.8
    assert "riesgo_hidrico" in r["flags"]
    assert r["potencial_extra"].startswith("potencial extra, revisar por completamiento y esquina")
    assert "039-087-006" in r["potencial_extra"] and "039-087-008" not in r["potencial_extra"]
    assert health[-1]["portal"] == "Ciudad 3D" and not health[-1]["falla"]


def test_caba_envelope_floors_per_unit(caba):
    """2,90 m between floors (Gonzalo, 19/11/2026): PB+12 / +9 / +6 / +4 with 2 set-backs; USAB PB+4 / +3 / +2."""
    k = caba["caba"]
    table = {(38, 45): "PB+12 + 2 retiros", (31.2, 38.2): "PB+9 + 2 retiros", (22.8, 29.8): "PB+6 + 2 retiros",
             (17.2, 24.2): "PB+4 + 2 retiros", (14.6, 14.6): "PB+4", (12, 12): "PB+3", (9, 9): "PB+2"}
    for (h, limit), label in table.items():
        assert motor_caba.envelope(375, 187.5, h, limit, None, k)["pisos"] == label
    # typical 8,66 x 43,30 lot in U.S.A.M.: 5 full floors + set-backs of 19,65 and 13,65 m depth, efficiency 0,85
    e = motor_caba.envelope(375, 187.5, 17.2, 24.2, 8.66, k)
    depth = 187.5 / 8.66
    assert e["eficiencia"] == 0.85
    assert e["m2"] == pytest.approx(187.5 * 0.85 * (5 + ((depth - 2) + (depth - 8)) / depth))


def test_caba_no_plusvalia_up_to_125_percent_of_the_fot(caba):
    small = dict(BUILDABLE, altura_max=[9.0, 0, 0, 0], altura_max_plano_limite=9.0)      # U.S.A.B. 0: PB+2
    caba["caba"]["m2_construibles_min"] = 0
    c3d = motor_caba.Ciudad3D(caba)
    c3d.cache["smp"]["039-087-007"] = small
    r = motor_caba.normalize(motor_caba.from_zonaprop(_zonaprop_items([(-34.56, -58.462, 617, 300000)])[0]), caba)
    motor_caba.evaluate(r, c3d, caba, 1580.9)
    assert r["m2_construibles"] < 1.25 * 5.0 * 617 and r["plusvalia_uva"] == 0


def test_caba_expensive_lot_is_discarded(caba):
    rows = motor_caba.process({"zonaprop": _zonaprop_items([(-34.5600, -58.4620, 617, 6000000)])}, caba, [])
    assert rows[0]["resultado"] == "descartado" and rows[0]["motivo_descarte"] == "incidencia_alta"


def test_caba_outside_the_city(caba):
    rows = motor_caba.process({"zonaprop": _zonaprop_items([(-34.47, -58.51, 900, 500000)])}, caba, [])
    assert rows[0]["motivo_descarte"] == "fuera_del_municipio"


def test_caba_geocoder_sends_street_and_number_apart(monkeypatch, caba):
    """First night run (17/11/2026): USIG answered the JSON string "Parametros incorrectos." and the run crashed."""
    sent = []

    def get(self, url, params=None, **kw):
        sent.append(params)
        if params.get("altura") is None:
            return FakeResp("Parametros incorrectos.")
        if params["calle"] == "Falsa":
            return FakeResp({"Normalizacion": {"TipoResultado": "ErrorCalleInexistente"}})
        return FakeResp({"GeoCodificacion": {"x": "100081.854642", "y": "107665.100091"}})
    monkeypatch.setattr(requests.Session, "get", get)
    c3d = motor_caba.Ciudad3D(caba)
    lat, lon = c3d.geocode("Av. Cabildo al 1200, Belgrano")
    assert sent[-1] == {"calle": "Av. Cabildo", "altura": 1200, "desambiguar": 1}
    assert -34.6 < lat < -34.5 and -58.5 < lon < -58.4
    assert c3d.geocode("Falsa 123") is None and c3d.geocode("Palermo") is None
    monkeypatch.setattr(requests.Session, "get", lambda self, url, params=None, **kw: FakeResp("Parametros incorrectos."))
    assert c3d.geocode("Moldes 2477") is None                          # a string answer: no position, no crash


def test_caba_generic_pin_is_located_by_address(caba):
    """18/11/2026: Mendoza lots loaded as 'Capital Federal' all sat on the portal's default pin."""
    pts = [(-34.5600, -58.4620, 617, 1500000)] * 4
    items = _zonaprop_items(pts)
    for i, it in enumerate(items):
        it["postingLocation"]["address"]["name"] = f"Calle Inventada {100 + i}"
    rows = motor_caba.process({"zonaprop": items}, caba, [])
    assert all(r["pin_generico"] for r in rows)
    assert {r["motivo_descarte"] for r in rows} == {"sin_ubicacion"}     # the test geocoder doesn't know them
    one = motor_caba.process({"zonaprop": _zonaprop_items(pts[:1])}, caba, [])[0]
    assert not one.get("pin_generico") and one["resultado"] == "oportunidad"


def test_caba_retries_a_503_and_recovers_after_an_outage(monkeypatch, caba):
    calls = {"n": 0}

    class Resp(FakeResp):
        def __init__(self, data, code=200):
            super().__init__(data)
            self.status_code = code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"{self.status_code} Server Error")

    def get(self, url, params=None, **kw):
        calls["n"] += 1
        if calls["n"] <= 30:                                   # an outage longer than the retries
            raise requests.ConnectionError("reset")
        return Resp(BUILDABLE)
    monkeypatch.setattr(requests.Session, "get", get)
    c3d = motor_caba.Ciudad3D(caba)
    for _ in range(20):
        try:
            c3d.buildable("039-087-007")
            break
        except RuntimeError:
            pass
    assert c3d.cache["smp"]["039-087-007"] == BUILDABLE and c3d.recoveries >= 1
