"""San Fernando: the eight decisions of Gonzalo on 26/11/2026 (municipios/san_fernando/GUIA_NORMATIVA.md, section 9),
over the Código de Edificación y Zonificación (Ord. 3603/91)."""

import json

from src import entorno
from src.config import load_config
from src.evaluate import multifamiliar, units
from tests import harness
from tests.test_municipios import _normativa, _point_in_zone, _zonaprop_items

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
SF = _normativa("san_fernando")
P = load_config("san_fernando")["productos"]


def _sf_row(monkeypatch, tmp_path, lat, lon, s, price):
    harness.offline(monkeypatch, tmp_path)
    from src import main
    cfg = load_config("san_fernando")
    cfg["productos"]["catastro"]["max_consultas_por_corrida"] = 0
    items = _zonaprop_items([(lat, lon, s, price)])
    items[0]["descriptionNormalized"] = ""          # the template's text gives its own lot (779 m2)
    return main.process({"zonaprop": items}, cfg, [], [])[0][0]


def test_r3_several_houses_per_lot():
    """#1 (3.5.6.7): 2 houses above 400 m2, 3 above 550, more above 700 by the density (4 people each): R3A 170 hab/ha
    = 1 every 235 m2, R3 250 = 160 m2. Today's 1 lot per 375 m2 / 15 m stays as the other product."""
    u = units(SF["R3A"], 1000, 20, P)
    assert u["agrupadas_calle"] == 4 and u["lotes_frente_propio"] == 1 and u["unidades_por_derecho"] == 4
    assert units(SF["R3"], 1000, 20, P)["agrupadas_calle"] == 6
    assert units(SF["R3"], 600, 20, P)["agrupadas_calle"] == 3          # cap 3 (> 550), density 3,75
    assert units(SF["R3A"], 600, 20, P)["agrupadas_calle"] == 2         # density 2,55
    assert units(SF["R3"], 500, 20, P)["agrupadas_calle"] == 2          # cap 2 (> 400)
    assert units(SF["R3"], 1000, 20, P)["agrupadas_acceso_comun"] == 8  # with approval: 320 hab/ha (PH ordinances)
    assert multifamiliar(SF["R3A"], 3000, P) == "No"                    # Gonzalo, 14/11: no building of flats
    assert {"casas_por_lote_3567", "requiere_cloaca_casas"} <= set(SF["R3A"]["flags"].split(";"))


def test_r3_premio_raises_the_density():
    """#3: FOT 1 -> 1,2 with premios (3.5.6.3) and the density in the same % (3.20.4): on 2 minimum lots (750 m2,
    30 m) R3A 1.000 m2 gives 1.000 x 1,2 / 235 = 5 houses instead of 4."""
    assert units(SF["R3A"], 1000, 30, P)["agrupadas_calle"] == 5
    assert units(SF["R3A"], 1000, 20, P)["agrupadas_calle"] == 4        # 20 m < 2 x 15 m: no premio


def test_bpn_grouped_houses():
    """#4 (3.9.1.13): 160 hab/ha = 1 house every 250 m2, FOT 0,70."""
    assert units(SF["BPN"], 3000, None, P)["agrupadas_calle"] == 12
    assert SF["BPN"]["fot"] == "0.7" and "saneamiento_obligatorio_bpn" in SF["BPN"]["flags"]


def test_industrial_zones_and_ddp_without_housing():
    """#5 and #6: I2, I2A and DI take a house only as an annex of the industry; DDP is a finished conjunto."""
    for z in ("I2", "I2A", "DI", "DDP"):
        assert SF[z]["regla_unidades"] == "Sin vivienda como producto"


def test_point_corrections_of_the_code():
    """#6 and #7: C4Ue multifamiliar FOT 1,2 from 450 m2; RR and Reconquista (RUM) multifamiliar from 3.000 m2."""
    assert SF["C4Ue"]["fot"] == "1.2"
    assert multifamiliar(SF["C4Ue"], 449, P) == "No" and multifamiliar(SF["C4Ue"], 450, P) == "Sí"
    assert SF["RR"]["fot"] == "1.4" and SF["RR"]["fos"] == "0.2"
    assert multifamiliar(SF["RR"], 2999, P) == "No" and multifamiliar(SF["RR"], 3000, P) == "Sí"
    rum = SF["RR: RUM-CR-VOAD-ZEU-ZUM-CRP-EPS"]
    assert rum["fot"] == "0.8" and "verificar_subzona_reconquista" in rum["flags"]
    assert units(rum, 1000, 20, P)["lotes_frente_propio"] == 1 and units(rum, 3000, None, P)["multifamiliar_unidades"] == 45
    assert SF["RRE"]["fot"] == "0.6"                                    # RRE is not RR


def test_density_cuts_c2a_and_c3(monkeypatch, tmp_path):
    """#2: 30 m2 per inhabitant (as Tigre): C2A 300 hab/ha -> 0,9 instead of FOT 3."""
    r = _sf_row(monkeypatch, tmp_path, *_point_in_zone("san_fernando", "C2A"), 2000, 300000)
    assert r["zona_fot_usado"] == "C2A" and r["fot_usado"] == 3
    assert r["fot_efectivo"] == 0.9 and r["m2_construibles"] == 1800 and "densidad 300" in r["limite_fot"]
    c3 = _sf_row(monkeypatch, tmp_path, *_point_in_zone("san_fernando", "C3"), 2500, 300000)
    assert c3["zona_fot_usado"] == "C3" and c3["fot_efectivo"] == 0.6 and c3["m2_construibles"] == 1500


def test_r2_premio(monkeypatch, tmp_path):
    """#3: R2 1,8 x 1,25 = 2,25 on 2 minimum lots (1.200 m2), with the density raised too (750 x 30 = 2,25)."""
    lat, lon = _point_in_zone("san_fernando", "R2")
    r = _sf_row(monkeypatch, tmp_path, lat, lon, 1500, 300000)
    assert r["zona_fot_usado"] == "R2" and r["fot_usado"] == 2.25 and r["fot_efectivo"] == 2.25
    assert "premio_ley_8912_aplicado" in r["flags"]
    small = _sf_row(monkeypatch, tmp_path, lat, lon, 1000, 300000)
    assert small["fot_usado"] == 1.8 and small["fot_efectivo"] == 1.8


def test_signals_aerodrome_and_sirga(monkeypatch, tmp_path):
    """#8: the DRC is ~1,5 km from the aerodrome (UE 2); the sirga uses the named rivers of OSM."""
    r = _sf_row(monkeypatch, tmp_path, *_point_in_zone("san_fernando", "DRC"), 3000, 600000)
    assert "cerca_aerodromo" in r["flags"]
    far = _sf_row(monkeypatch, tmp_path, *_point_in_zone("san_fernando", "C2A"), 3000, 600000)
    assert "cerca_aerodromo" not in far["flags"]                        # C2A is not a zone of tall buildings
    rivers = json.loads((ROOT / "municipios/san_fernando/fuentes/rios_osm.geojson").read_text(encoding="utf-8"))
    lujan = next(f for f in rivers["features"] if f["properties"]["nombre"] == "Río Luján")
    lon, lat = lujan["geometry"]["coordinates"][0]
    env = entorno.for_config(load_config("san_fernando"))
    d, name = env.water_m(lat, lon)
    assert d < 1 and name == "Río Luján"
    assert not any(f["properties"]["nombre"] == "Arroyo Pavón" for f in rivers["features"])
