"""Online Critical Pseudepigrapha to Text-Fabric conversion."""

from .release_identity import CONVERTER_VERSION

__version__ = CONVERTER_VERSION

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
