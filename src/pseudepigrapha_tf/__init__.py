"""Online Critical Pseudepigrapha to Text-Fabric conversion."""

__version__ = "0.2.0"

from .apparatus import Apparatus
from .classifications import HistoricalClassifications
from .conversion import build_tf_data
from .feature_docs import edge_feature_contracts, serialized_feature_contract
from .metadata import WorkMetadata
from .translations import Translations

__all__ = [
    "Apparatus",
    "HistoricalClassifications",
    "Translations",
    "WorkMetadata",
    "edge_feature_contracts",
    "serialized_feature_contract",
    "build_tf_data",
    "__version__",
]
