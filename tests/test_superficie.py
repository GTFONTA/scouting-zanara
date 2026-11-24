"""Listings that load the buildable m2 as the lot (CABA errors #1-#7, municipios/caba/REGISTRO_ERRORES.md)."""

import pytest

from src.normalize import lot_from_text


@pytest.mark.parametrize("name, titulo, descripcion, surface, front, depth, expected", [
    ("#1 medidas del texto", "Venta Lote en Congreso", "AV ENTRE RIOS E INDEPENDENCIA LOTE 7.68 X 34.77", 2500, 7, None, 267),
    ("#2 frente x largo", "Lote en Venta", "permite la construcción de hasta 1.753 m² totales", 1530, 9, 16, 144),
    # the same listings as Zonaprop's results page writes them (descriptionNormalized)
    ("#1 texto de Zonaprop", "Venta Lote en Congreso",
     "lote 7. 68 X 34. 77. 25oo M2 vendibles sobre av entre rios. usaa altura maxima", 2500, None, None, 267),
    ("#5 texto de Zonaprop", "Venta Lote Villla Urquiza",
     "Superficie de parcela: 212m²· Frente: 12, 30 m 2· Superficie total vendible estimada: 1. 116 m² + pb. "
     "Tenemos mas lotes no publicados", 1395, None, None, 212),
    ("#3 lote en el texto", "Córdoba 4100 Lote en Esquina Petit Hotel Capacidad Constructiva 1200 m No Aph",
     "LOTE 110 mts cap constr 1200 sobre p. hotel. Capacidad constructiva 1200 mts", 1200, None, None, 110),
    ("#5 superficie de parcela", "Venta Lote", "Superficie de parcela: 212m2 Frente: 12,30 m", 1395, 12, 17.3, 212),
    ("#6 construibles", "Terreno Thames", "7.75 x 17.41 1.700 metros cuadrados construibles", 1700, 7, 17, 119),
    ("#7 vendible", "Terreno en Caballito", "-8.67 x 39.97 mts - Altura 22.80 mts -Sup vendible 2056 mts", 2056, None, None, 347),
    ("lote con construibles aparte", "Lote 480 m² en Boulogne – 550 m² Construibles", "", 478, None, None, None),
    ("construcción existente", "Terreno De 300 M² Con Construcción Existente", "", 300, None, None, None),
    ("varios lotes", "2 Lotes en Barrio La Candelaria", "Lote de 522 m2 cada uno", 1095, None, None, None),
    ("lotes 11 y 12, texto pegado", "Terreno en Venta Las Lomas de San Isidro - Zona Jockey",
     "lomas de san isidrolote N° 11 y 12 - 1705, 23 metros cuadrados. Opción de comprar por separado: 1 lote de 822, 95 m2 "
     "y otro lote de 882, 28 m2", 1705, None, None, None),
    ("varias residencias", "Casa en Boating Club", "Superficie de terreno: 2099 m2 ... Superficie de terreno: 809 m2", 2099, 14, None, None),
    ("medidas normales", "Lote 10 x 40", "Lote de 10 x 40 en zona residencial", 400, 10, 40, None),
])
def test_lot_from_text(name, titulo, descripcion, surface, front, depth, expected):
    lot, why = lot_from_text({"titulo": titulo, "descripcion": descripcion}, surface, front, depth)
    assert (round(lot) if lot else None) == expected, (name, why)


def test_only_buildable_and_no_lot_is_flagged():
    assert lot_from_text({"titulo": "Lote", "descripcion": "1.500 m2 construibles"}, 1500, None, None) == (None, "construible")


def test_a_yard_is_not_the_lot():
    """San Isidro, Galpón Beccar (23/11/2026): 'Terreno de 250m2 aprox descubierto' is part of a 1.700 m2 property."""
    r = {"titulo": "Galpón - Beccar", "descripcion": "Nave de 1100 m2 cubiertos. Terreno de 250m2 aprox descubierto con portón"}
    assert lot_from_text(r, 1700, None, None) == (None, "")


@pytest.mark.parametrize("name, titulo, descripcion, covered, surface, expected", [
    # CABA errors #8-#10 (Gonzalo, 24/11/2026): the listing's surface is the covered area
    ("#8 tot = cub y medidas del lote", "Terreno a La Venta Recoleta",
     "ideal desarrollo en altura. Lote 7. 50 x 30 metros. terreno apto para construir: Planta Baja + 7 pisos", 1400, 1400, 225),
    ("#9 cubiertos sobre lote", "Palermo: Galpon 562 m² con Entrada Para Camiones",
     "galpón de 562 M2 cubiertos sobre lote de 525 M2 (8, 79/8, 66 X <span>Ver datos</span>) - usab2", 562, 562, 525),
    ("Rolón: lote 10x40", "Edificio Comercial 1400 m² Cubiertos Sobre Avda Rolon",
     "Espectacular edificio comercial sobre lote 10x40m2, 1400 m2 cubiertos sobre Avenida Rolon", 1400, 1400, 400),
    ("medidas de un ambiente", "Venta Casa En Acassuso", "PRIMER PISO: - Play Room (6x9) - 3 Dormitorios", 499, 499, None),
    ("las medidas son la superficie", "1188 m² de Terreno en Pleno Martínez",
     "Excelente lote de 17, 32 x 68, 60 de fondo, total: 1188 m2. galpón de 8, 60 x 16", 1188, 1188, None),
    ("#10 sin lote en el texto", "Casa en Palermo Soho", "joya de 354 m² cubiertos sobre lote propio", 345, 365, None),
])
def test_covered_surface(name, titulo, descripcion, covered, surface, expected):
    lot, why = lot_from_text({"titulo": titulo, "descripcion": descripcion, "superficie_cubierta_m2": covered},
                             surface, None, None)
    assert (round(lot) if lot else None) == expected, (name, why)


def test_a_lot_corrected_in_one_publication_serves_the_others():
    """San Isidro, 24/11/2026: 'Galpón - Beccar', 1783 m2 covered on a 1084 m2 lot (Zonaprop's text); the Mercado
    Libre copy, without description, says 1783 m2 at the same pin and price."""
    from src.config import load_config
    from src.dedupe import share_surface
    zp = {"id": "zp", "precio_usd": 800000, "superficie_m2": 1084, "superficie_aviso_m2": 1783, "lat": -34.4748,
          "lon": -58.5423, "direccion": "Jorge Newbery al 1300", "superficie_fuente": "superficie del lote en el texto",
          "alertas": []}
    ml = {"id": "ml", "precio_usd": 800000, "superficie_m2": 1783, "lat": -34.4748, "lon": -58.5423,
          "direccion": "Jorge Newbery Al 1300", "superficie_fuente": "total", "alertas": []}
    other = {**ml, "id": "otro", "superficie_m2": 1400, "alertas": []}
    share_surface([zp, ml, other], load_config())
    assert ml["superficie_m2"] == 1084 and ml["superficie_aviso_m2"] == 1783
    assert other["superficie_m2"] == 1400            # another surface: not the same listing
