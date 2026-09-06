"""Online Critical Pseudepigrapha to Text-Fabric conversion."""

__version__ = "0.1.0"

from .apparatus import Apparatus
from .conversion import build_tf_data
from .metadata import WorkMetadata

__all__ = ["Apparatus", "WorkMetadata", "build_tf_data", "__version__"]
