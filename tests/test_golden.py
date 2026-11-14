"""Golden tests: reprocessing real runs must give exactly the saved results (hits, route, units, incidence,
every intermediate value, the summary and the mail).

If a change is MEANT to change results (a rule Gonzalo asked for), regenerate the expected files with
    python -m pytest tests/test_golden.py --regenerar
and review the diff of the summaries before committing.
"""

import difflib

import pytest

from tests import harness


@pytest.mark.parametrize("run", harness.RUNS)
def test_golden(run, monkeypatch, tmp_path, request):
    out = harness.reprocess(run, monkeypatch, tmp_path)
    if request.config.getoption("--regenerar"):
        harness.save_expected(run, out)
        pytest.skip("esperados regenerados")
    exp = harness.expected(run)
    for name in ("resumen.txt", "resultado.csv", "mail.html"):
        if out[name] != exp[name]:
            diff = "\n".join(list(difflib.unified_diff(exp[name].splitlines(), out[name].splitlines(),
                                                       "esperado", "obtenido", lineterm="", n=1))[:60])
            pytest.fail(f"{run}/{name} cambió:\n{diff}")
