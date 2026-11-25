"""Automatic runs while the PC is on (Gonzalo, 24/11/2026): the rules of src/agenda.py."""

import json
from datetime import datetime

from src.agenda import Run, decide, pending
from src.config import load_config

K = load_config()["agenda"]
TUE = datetime(2026, 12, 1, 11, 0)            # a Tuesday; that week's San Isidro ran on Monday 30/11
SI_DONE = Run("san_isidro", datetime(2026, 11, 30, 10, 30), True)
LEFT = ["mercadolibre: fichas pendientes: 300 quedan para la próxima corrida"]


def test_caba_first_until_its_first_download_is_done():
    m, why = decide(TUE, [SI_DONE, Run("caba", datetime(2026, 11, 25, 3, 0), True, LEFT)], K)
    assert m == "caba" and "fichas pendientes" in why
    done = Run("caba", datetime(2026, 11, 25, 3, 0), True, [])
    assert decide(TUE, [SI_DONE, done], K)[0] == "tigre"                      # never ran
    tigre = Run("tigre", datetime(2026, 11, 26, 11, 0), True, [])
    assert decide(TUE, [SI_DONE, done, tigre], K)[0] == "san_fernando"


def test_second_batch_the_same_day_four_hours_apart():
    morning = Run("caba", TUE.replace(hour=10), True, LEFT)
    assert decide(TUE.replace(hour=13), [SI_DONE, morning], K)[0] is None       # 3 h later
    m, why = decide(TUE.replace(hour=14), [SI_DONE, morning], K)
    assert m == "caba" and "2 de 2" in why
    later = Run("caba", TUE.replace(hour=14), True, LEFT)
    assert decide(TUE.replace(hour=19), [SI_DONE, morning, later], K) == (None, "hoy ya corrió caba")


def test_one_municipio_per_day_and_never_two_at_once():
    tigre_today = Run("tigre", TUE.replace(hour=9), True, [])
    assert decide(TUE, [SI_DONE, tigre_today], K) == (None, "hoy ya corrió tigre")
    going = Run("caba", TUE.replace(hour=10, minute=30), False)
    assert "en curso" in decide(TUE, [SI_DONE, going], K)[1]


def test_san_isidro_goes_first():
    monday = datetime(2026, 11, 30, 9, 0)
    assert decide(monday, [], K)[0] is None                                     # before 10:30
    assert decide(monday.replace(hour=12), [], K) == (None, "esperando la corrida semanal de San Isidro")
    assert decide(monday.replace(hour=12), [SI_DONE], K) == (None, "hoy ya corrió san_isidro")
    # San Isidro's task didn't start for 2 days: the queue goes on anyway
    assert decide(datetime(2026, 12, 2, 12, 0), [], K)[0] == "caba"


def test_weekly_rotation_once_everything_is_downloaded():
    done = [SI_DONE] + [Run(m, datetime(2026, 11, 28, 11, 0), True, []) for m in ("caba", "tigre", "san_fernando")]
    assert decide(TUE, done, K)[0] == "caba"                                    # Tuesday
    assert decide(datetime(2026, 12, 2, 11, 0), done, K)[0] == "tigre"          # Wednesday
    assert decide(datetime(2026, 12, 4, 11, 0), done, K)[0] is None             # Friday: free (Vicente López later)


def test_a_municipio_that_only_fails_is_skipped():
    done = Run("caba", datetime(2026, 11, 25, 3, 0), True, [])
    broken = [Run("tigre", datetime(2026, 11, 26 + i, 11, 0), True, ["zonaprop: falla"]) for i in range(3)]
    assert decide(TUE, [SI_DONE, done] + broken, K)[0] == "san_fernando"


def test_pending_reads_what_the_run_left(tmp_path):
    (tmp_path / "salud_final.json").write_text(json.dumps([
        {"portal": "zonaprop", "falla": False, "errores": [],
         "avisos_menores": ["primera descarga en curso: 1 búsqueda(s) sin terminar"]},
        {"portal": "Ciudad 3D", "falla": False, "errores": ["tope de 3000 consultas por corrida: 12 consultas quedan "
                                                            "para la próxima corrida"]},
        {"portal": "mercadolibre", "falla": True, "errores": ["bloqueo abriendo fichas: x"], "avisos_menores": []}]),
        encoding="utf-8")
    finished, left = pending(tmp_path)
    assert finished and len(left) == 3 and left[-1] == "mercadolibre: falla"
