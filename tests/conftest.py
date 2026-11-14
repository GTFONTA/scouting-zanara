def pytest_addoption(parser):
    parser.addoption("--regenerar", action="store_true", help="regenerar los resultados esperados de los golden tests")
