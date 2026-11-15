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
    assert hit["fot_usado"] == 3.0 and hit["m2_construibles"] == 3600
    assert hit["requiere_cloaca"] and "requiere_cloaca_para_max" in hit["flags"]    # C1-C4: Gonzalo, 14/11
    assert "requiere_cloaca_multifamiliar" not in hit["flags"]
    assert outside["motivo_descarte"] == "fuera_del_partido"


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
             "parcelas_linderas": {"aph_linderas": False}, "catalogacion": {"proteccion": None},
             "distrito_especial": [], "tipica": "T", "afectaciones": {"riesgo_hidrico": 1}, "superficie_parcela": 613.8}
PLUS = {"plusvalia_em": 111925.8, "plusvalia_pl": 0, "plusvalia_sl": 111925.8, "incidencia_uva": 420.0}
UVA = {"results": [{"detalle": [{"fecha": "2026-11-14", "valor": 2196.12}]}]}


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
    assert r["fot_usado"] == 7.0 and r["tipo_fot"] == "perímetro libre"
    assert r["escenario"] == "envolvente" and r["m2_construibles"] == round(613.79 * 0.65 * 12)
    assert r["plusvalia_usd"] == round(111925.8 * 2196.12 / 1580.9)
    assert r["incidencia_total_usd_m2"] > r["incidencia_usd_m2"]
    assert r["resultado"] == "oportunidad" and r["ratio_incidencia"] <= 0.8
    assert "riesgo_hidrico" in r["flags"]
    assert health[-1]["portal"] == "Ciudad 3D" and not health[-1]["falla"]


def test_caba_expensive_lot_is_discarded(caba):
    rows = motor_caba.process({"zonaprop": _zonaprop_items([(-34.5600, -58.4620, 617, 6000000)])}, caba, [])
    assert rows[0]["resultado"] == "descartado" and rows[0]["motivo_descarte"] == "incidencia_alta"


def test_caba_outside_the_city(caba):
    rows = motor_caba.process({"zonaprop": _zonaprop_items([(-34.47, -58.51, 900, 500000)])}, caba, [])
    assert rows[0]["motivo_descarte"] == "fuera_del_municipio"
