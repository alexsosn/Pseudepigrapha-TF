"""Online Critical Pseudepigrapha to Text-Fabric conversion."""

__version__ = "0.1.0"

from .document_apparatus import Apparatus
from .document_conversion import build_tf_data

__all__ = ["Apparatus", "build_tf_data", "__version__"]
