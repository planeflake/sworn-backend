# Re-export app.models to support legacy imports
# This allows both "from models.core import X" and "from app.models.core import X" to work
from app.models.core import *