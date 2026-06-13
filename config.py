import os
from dotenv import load_dotenv

load_dotenv()

# Autodesk Platform Services
APS_HOST = "https://developer.api.autodesk.com"
APS_CLIENT_ID = os.environ.get("APS_CLIENT_ID", "")
APS_CLIENT_SECRET = os.environ.get("APS_CLIENT_SECRET", "")
APS_SCOPES = "data:read data:write data:create bucket:create bucket:read"
APS_BUCKET_KEY = os.environ.get("APS_BUCKET_KEY", "cyvl-hack-lidar")

# Data paths
LAZ_DIR = os.environ.get("LAZ_DIR", os.path.join(os.path.dirname(__file__), "data", "raw"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "data", "output"))

# Processing defaults
DEFAULT_VOXEL_SIZE = float(os.environ.get("VOXEL_SIZE", "0.10"))
DEFAULT_ROI_M = float(os.environ.get("ROI_M", "200.0"))
DEFAULT_CONTOUR_INTERVAL = float(os.environ.get("CONTOUR_INTERVAL", "1.0"))
