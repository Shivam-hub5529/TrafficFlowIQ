"""Project-wide constants and paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SERVING_DIR = DATA_DIR / "serving"
MODELS_DIR = ROOT / "models"

STEP_MIN = 5                    # data resolution (minutes)
HIST_STEPS = 12                 # 60 minutes of history
HORIZON_STEPS = 6               # 30 minutes ahead
HORIZONS_MIN = [5, 10, 15, 20, 25, 30]
QUEUE_RATIO = 0.60              # queued when speed <= 60% of free-flow speed

# Split (whole days, chronological) and leakage purge gap
TRAIN_FRAC, VAL_FRAC = 0.70, 0.15
PURGE_MIN = 90

# Risk bands shown in the app
RISK_LOW, RISK_HIGH = 0.30, 0.60

# Physics-check constants (simple, documented, easy to tune)
JAM_DENSITY = 150.0             # veh/km/lane
CAPACITY_PL = 2500.0            # veh/h/lane
CONSERVATION_TOL = 0.20         # relative tolerance for vehicle conservation

QUEUE_MODEL_VERSION = "queue-v1.0.0"
RECON_MODEL_VERSION = "recon-v1.0.0"
