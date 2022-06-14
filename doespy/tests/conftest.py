

def pytest_addoption(parser):
    parser.addoption("--suite", action="store")
    parser.addoption("--id", action="store", default="last")
    parser.addoption("--idref", action="store", default="expected")
