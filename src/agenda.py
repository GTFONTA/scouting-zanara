"""Automatic runs while the PC is on (Gonzalo, 24/11/2026).

The task "Scouting automático" of the Windows Task Scheduler starts this at logon, at unlock and every hour. Each
time it decides whether a run is due, runs at most one (correr_semanal.ps1 -Municipio <slug>, which writes the log
and sends the mail) and exits. San Isidro keeps its own weekly task (Monday 10:30). Rules (config.yaml, agenda:):

  1. Never two runs at the same time: a run started less than horas_max_corrida ago without salud_final.json is
     still going (whatever started it).
  2. San Isidro first: on Monday nothing runs before 10:30, and after that nothing until this week's San Isidro run
     exists (at most espera_san_isidro_max_h, in case its task didn't start).
  3. One municipio per day with traffic to the portals. A municipio still in its first download may run up to
     tandas_por_dia times that day, horas_entre_tandas apart.
  4. Which one: the first of primera_descarga that is not finished yet (never ran, or its last run left something
     for the next one: incremental sweep, Mercado Libre detail pages, Ciudad 3D queries, a blocked portal); once all
     are finished, the municipio of the weekday in rotacion (Monday first) if it didn't run today. A municipio whose
     last reintentos_falla runs only failed (a blocked or broken search, no progress) is skipped so the queue goes
     on; each of those runs already reported the failure by mail.

    python -m src.agenda          # decide and run
    python -m src.agenda --ver    # only say what it would do and why
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .config import ROOT, load_config

RUN_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}$")          # real runs; reprocesses have a suffix
SI = "san_isidro"
LEFT_FOR_NEXT = ("primera descarga en curso", "fichas pendientes", "quedan para la próxima corrida",
                 "se dejó de consultar", "se sigue en la próxima corrida")


@dataclass
class Run:
    municipio: str
    start: datetime
    finished: bool
    pending: list = field(default_factory=list)       # what the run left for the next one


def pending(run_dir: Path) -> tuple[bool, list[str]]:
    """(finished, what it left for the next run). Finished = it wrote salud_final.json (resumen.txt for runs made
    before the agenda existed)."""
    final = run_dir / "salud_final.json"
    source = final if final.exists() else run_dir / "salud.json"
    finished = final.exists() or (run_dir / "resumen.txt").exists()
    if not source.exists():
        return finished, ["la corrida no dejó salud.json"]
    left = []
    for entry in json.loads(source.read_text(encoding="utf-8")):
        notes = (entry.get("avisos_menores") or []) + (entry.get("errores") or [])
        left += [f"{entry.get('portal')}: {n}" for n in notes if any(k in n for k in LEFT_FOR_NEXT)]
        if entry.get("falla") and not any(k in " ".join(notes) for k in LEFT_FOR_NEXT):
            left.append(f"{entry.get('portal')}: falla")
    return finished, left


def runs(root: Path = ROOT) -> list[Run]:
    out = []
    for slug_dir, slug in [(root / "runs", SI)] + [(d, d.name) for d in (root / "runs").iterdir()
                                                  if d.is_dir() and (root / "municipios" / d.name).is_dir()]:
        for d in slug_dir.iterdir():
            if d.is_dir() and RUN_DIR.match(d.name):
                done, left = pending(d)
                out.append(Run(slug, datetime.strptime(d.name, "%Y-%m-%d_%H%M"), done, left))
    return sorted(out, key=lambda r: r.start)


def _monday_1030(now: datetime) -> datetime:
    monday = (now - timedelta(days=now.weekday())).replace(hour=10, minute=30, second=0, microsecond=0)
    return monday if now >= monday else monday - timedelta(days=7)


def decide(now: datetime, history: list[Run], k: dict) -> tuple[str | None, str]:
    """(municipio to run or None, why). Pure: the tests call it with made-up histories."""
    going = [r for r in history if not r.finished and now - r.start < timedelta(hours=k["horas_max_corrida"])]
    if going:
        return None, f"hay una corrida en curso ({going[-1].municipio}, desde {going[-1].start:%d/%m %H:%M})"
    if now.weekday() == 0 and now.hour * 60 + now.minute < 10 * 60 + 30:
        return None, "lunes antes de las 10:30: primero corre San Isidro"
    monday = _monday_1030(now)
    last_si = max((r.start for r in history if r.municipio == SI), default=None)
    if (last_si is None or last_si < monday) and now - monday < timedelta(hours=k["espera_san_isidro_max_h"]):
        return None, "esperando la corrida semanal de San Isidro"

    def last(m):
        return next((r for r in reversed(history) if r.municipio == m and r.finished), None)

    def unfinished(m):
        r = last(m)
        return r is None or bool(r.pending)

    def stuck(m):            # only failures, no progress, in its last runs: let the queue go on
        done = [r for r in history if r.municipio == m and r.finished][-k["reintentos_falla"]:]
        return len(done) == k["reintentos_falla"] and all(
            r.pending and all(x.endswith(": falla") for x in r.pending) for r in done)
    today = [r for r in history if r.start.date() == now.date()]
    if today:
        m = today[0].municipio
        mine = [r for r in today if r.municipio == m]
        if m in k["primera_descarga"] and unfinished(m) and not stuck(m) and len(mine) < k["tandas_por_dia"] \
                and now - mine[-1].start >= timedelta(hours=k["horas_entre_tandas"]):
            return m, f"otra tanda de la primera descarga de {m} ({len(mine) + 1} de {k['tandas_por_dia']} hoy)"
        return None, f"hoy ya corrió {m}"
    for m in k["primera_descarga"]:
        if unfinished(m) and not stuck(m):
            r = last(m)
            why = "nunca corrió" if r is None else "; ".join(r.pending[:2])
            return m, f"primera descarga de {m} sin terminar ({why})"
    m = (k["rotacion"] + [None] * 7)[now.weekday()]
    if m and m != SI:
        return m, f"rotación semanal: hoy le toca a {m}"
    return None, "nada para hoy"


def log(text: str, k: dict) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M} {text}"
    print(line)
    p = ROOT / k["log"]
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", action="store_true", help="solo decir qué haría y por qué")
    args = ap.parse_args()
    k = load_config()["agenda"]
    m, why = decide(datetime.now(), runs(), k)
    if args.ver or not m:
        (print if args.ver else lambda t: log(t, k))(f"{'correría ' + m if m else 'no corre nada'}: {why}")
        return
    log(f"corre {m}: {why}", k)
    script = ROOT / "correr_semanal.ps1"
    code = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                           "-Municipio", m], cwd=ROOT).returncode
    log(f"terminó {m} (código {code})", k)
    sys.exit(code)


if __name__ == "__main__":
    main()
