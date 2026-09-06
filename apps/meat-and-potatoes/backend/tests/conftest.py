import os
import tempfile

# Point the app at a throwaway sqlite file before anything imports config.
_tmp = tempfile.mkdtemp(prefix="map-test-")
os.environ.setdefault("DB_PATH", os.path.join(_tmp, "test.db"))
os.environ.setdefault("MAP_PROVIDER", "mock")
os.environ.setdefault("SCRAPERAPI_KEY", "test-key")
