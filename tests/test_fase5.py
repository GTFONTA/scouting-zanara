"""Fase 5: register of comparables, value of the zone and margin (offline, synthetic data)."""

from src import margin, registro
from src.config import load_config

CFG = load_config()
TODAY = "2026-11-15"


def _comp(producto, usd_m2, lat=-34.47, lon=-58.52, loc="Beccar", m2=100, estrenar="si", visto=TODAY, i=[0]):
    i[0] += 1
    return {"portal": "zonaprop", "id": str(i[0]), "producto": producto, "localidad": loc, "lat": lat, "lon": lon,
            "m2": m2 + 10 * i[0], "precio_usd": usd_m2 * (m2 + 10 * i[0]), "usd_m2": usd_m2, "a_estrenar": estrenar,
            "primera_vez": visto, "ultima_vez": visto}


def test_inactive_by_default():
    assert CFG["margen"]["activo"] is False                         # the run doesn't change until Gonzalo decides
    assert CFG["margen"]["costo_obra_usd_m2"] == {"multifamiliar": 1800, "casas": 1800}
    assert CFG["margen"]["costo_loteo_bc_usd_m2_bruto"] == 30


def test_register_collect_and_merge():
    rows = [
        {"portal": "zonaprop", "id": "1", "tipologia": "departamento", "precio_usd": 300000, "superficie_cubierta_m2": 100,
         "lat": -34.47, "lon": -58.52, "titulo": "Depto a estrenar 3 amb", "localidad": "Beccar"},
        {"portal": "zonaprop", "id": "2", "tipologia": "terreno", "precio_usd": 400000, "superficie_terreno_m2": 800,
         "lat": -34.47, "lon": -58.52, "titulo": "Lote en barrio cerrado Los Cardos", "localidad": "Beccar"},
        {"portal": "zonaprop", "id": "3", "tipologia": "terreno", "precio_usd": 400000, "superficie_terreno_m2": 800,
         "lat": -34.47, "lon": -58.52, "titulo": "Lote en Beccar", "localidad": "Beccar"},              # open lot: no
        {"portal": "zonaprop", "id": "4", "tipologia": "casa", "precio_usd": 5000, "superficie_cubierta_m2": 200,
         "lat": -34.47, "lon": -58.52, "titulo": "Casa", "localidad": "Beccar"},                        # 25 USD/m2: no
    ]
    got = registro.collect(rows, None, CFG, today="2026-11-02")
    assert [(x["id"], x["producto"], x["usd_m2"], x["a_estrenar"]) for x in got] == \
        [("1", "departamento", 3000, "si"), ("2", "lote_barrio_cerrado", 500, "no")]
    later = registro.collect([{**rows[0], "precio_usd": 280000}], None, CFG, today=TODAY)
    merged = registro.merge(got, later)
    flat = next(x for x in merged if x["id"] == "1")
    assert flat["primera_vez"] == "2026-11-02" and flat["ultima_vez"] == TODAY and flat["usd_m2"] == 2800


def test_zone_value_steps():
    near = [_comp("departamento", 3000 + 10 * k) for k in range(5)]
    far = [_comp("departamento", 2000, lat=-34.50, lon=-58.55, loc="Boulogne Sur Mer") for _ in range(5)]
    used = [_comp("departamento", 9000, estrenar="no") for _ in range(5)]            # not a estrenar: ignored
    old = [_comp("departamento", 9000, visto="2025-01-01") for _ in range(5)]        # too old: ignored
    reg = near + far + used + old
    v = margin.zone_value(reg, "departamento", -34.4705, -58.5205, "Beccar", CFG, TODAY)
    assert v == {"usd_m2": 3020, "n": 5, "escalon": "500 m"}
    v = margin.zone_value(reg, "departamento", -34.40, -58.60, "Beccar", CFG, TODAY)
    assert v["escalon"] == "localidad" and v["usd_m2"] == 3020
    v = margin.zone_value(reg, "departamento", None, None, "Villa Adelina", CFG, TODAY)
    assert v["escalon"] == "partido" and v["n"] == 10
    assert margin.zone_value(near[:4], "departamento", -34.47, -58.52, "Beccar", CFG, TODAY)["usd_m2"] is None


def test_same_unit_twice_counts_once():
    a = _comp("departamento", 3000)
    reg = [a, {**a, "id": "x", "portal": "mercadolibre"}] + [_comp("departamento", 3000) for _ in range(3)]
    assert margin.zone_value(reg, "departamento", -34.47, -58.52, "Beccar", CFG, TODAY)["usd_m2"] is None   # 4, not 5


def test_margin_formulas():
    # 3.500 de venta - 1.800 de obra - 400 de incidencia = 1.300 por m2; sobre costo 1.300 / 2.200
    assert margin.margin_built(3500, 400, 2000, 1800, 0) == {"usd_m2": 1300, "total": 2_600_000, "pct": 59.1}
    # lote de barrio cerrado a 200/m2 x 75% vendible - 30 de desarrollo - 50 de tierra = 70 por m2 bruto
    assert margin.margin_loteo(200, 50, 10000, 30, 0.75, 0) == {"usd_m2": 70, "total": 700_000, "pct": 87.5}


def test_evaluate_picks_the_best_via():
    reg = [_comp("departamento", 3500) for _ in range(5)] + [_comp("casa", 2500, estrenar="no") for _ in range(5)]
    r = {"precio_usd": 800000, "superficie_m2": 1000, "m2_construibles": 2000, "multifamiliar_unidades": 20,
         "lotes_frente_propio": 3, "agrupadas_calle": "", "agrupadas_acceso_comun": "", "lotes_calle_interna": "",
         "lat_usada": -34.47, "lon_usada": -58.52, "localidad": "Beccar"}
    ev = margin.evaluate(r, reg, CFG, TODAY)
    assert ev["margen_depto_usd_m2"] == 3500 - 1800 - 400 and ev["margen_casa_usd_m2"] == 2500 - 1800 - 400
    assert ev["margen_mejor_producto"] == "multifamiliar" and ev["margen_mejor_pct"] == 59.1
    assert "margen_lote_bc_pct" not in ev                       # < 5.000 m2: no internal street loteo
