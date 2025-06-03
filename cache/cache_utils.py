import pickle
from typing import Any

def serialize_embedding(embedding) -> bytes:
    """Serialize numpy array embedding for storage."""
    return pickle.dumps(embedding)

def deserialize_embedding(data: bytes) -> Any:
    """Deserialize embedding from storage."""
    return pickle.loads(data) 