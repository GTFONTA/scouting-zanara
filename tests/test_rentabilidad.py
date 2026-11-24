"""Expected profit per m2 (Gonzalo, 23/11/2026): incidencia, costo total, venta and the difference."""

import pytest

from src import rentabilidad
from src.config import load_config


@pytest.fixture(scope="module")
def caba():
    return load_config("caba")


@pytest.fixture(scope="module")
def san_isidro():
    return load_config()


def test_sale_value_by_barrio(caba):
    v = rentabilidad.SaleValues(caba)
    assert v.get("Palermo")[0] == 4242                       # a estrenar (AEstrenar)
    assert v.get("Palermo Soho")[0] == 4242                  # sub-barrio of the portal, by prefix
    assert v.get("Villa Urquiza")[0] == round(2794 * 1.25)   # no figure for new flats: general x 1,25
    assert v.get("Centro / Microcentro")[0] == round(1801 * 1.25)   # alias -> San Nicolás
    assert v.get("San Cristobal")[0] == round(1865 * 1.25)   # without the accent
    assert v.get("Barrio inventado")[1].startswith("zona sin dato")


def test_tigre_uses_the_partido():
    v = rentabilidad.SaleValues(load_config("tigre"))
    assert v.get("Nordelta")[0] == v.get("Don Torcuato")[0] == round(2702 * 1.25)


def test_multifamiliar_caba_counts_the_plusvalia(caba):
    r = {"resultado": "oportunidad", "precio_usd": 300000, "plusvalia_usd": 60000, "m2_construibles": 1200,
         "barrio": "Palermo Hollywood"}
    rentabilidad.apply(r, rentabilidad.SaleValues(caba), caba)
    assert r["rent_incidencia_usd_m2"] == 300                # (300.000 + 60.000) / 1.200
    assert r["rent_costo_total_usd_m2"] == 2100              # + 1.800 of works
    assert r["rent_venta_usd_m2"] == 4242
    assert r["rent_diferencia_usd_m2"] == 2142 and r["rent_por"] == "m² vendible"
    assert r["rent_total_usd"] == 2142 * 1200


def test_loteo_with_internal_street_loses_the_street(san_isidro):
    r = {"resultado": "oportunidad", "via": "loteo_agrupadas", "precio_usd": 1000000, "superficie_m2": 10000,
         "mediana_usd_m2_lote": 800, "mejor_producto": "loteo con calle interna (con aprobación)", "localidad": "Beccar"}
    rentabilidad.apply(r, rentabilidad.SaleValues(san_isidro), san_isidro)
    assert r["rent_venta_usd_m2"] == 600                     # 800 x (1 - 25% de calle)
    assert r["rent_costo_total_usd_m2"] == 130               # 100 of land + 30 of development
    assert r["rent_diferencia_usd_m2"] == 470 and r["rent_por"] == "m² de terreno"


def test_pba_takes_the_localidad_before_the_portal_barrio(san_isidro):
    r = {"resultado": "oportunidad", "via": "multifamiliar", "precio_usd": 300000, "m2_construibles": 1000,
         "localidad": "Acassuso", "barrio": "San Isidro"}
    rentabilidad.apply(r, rentabilidad.SaleValues(san_isidro), san_isidro)
    assert r["rent_venta_usd_m2"] == round(2575 * 1.25)


def test_order_puts_the_best_profit_first():
    rows = [{"rent_diferencia_usd_m2": 100}, {"rent_diferencia_usd_m2": None}, {"rent_diferencia_usd_m2": 900}]
    assert [r["rent_diferencia_usd_m2"] for r in sorted(rows, key=rentabilidad.order_key)] == [900, 100, None]
