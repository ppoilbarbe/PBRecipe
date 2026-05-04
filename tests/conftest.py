import os


def pytest_configure(config):
    # Allows Qt tests to run in headless environments (CI, etc.).
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
