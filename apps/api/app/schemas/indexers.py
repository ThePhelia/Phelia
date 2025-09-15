from pydantic import BaseModel
from typing import Optional, Dict, Any

class Indexer(BaseModel):
    id: str
    name: str
    is_private: bool
    configured: bool

class IndexerConnectIn(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    apikey: Optional[str] = None

class IndexerConnectOut(BaseModel):
    id: str
    configured: bool
    message: str

class IndexerTestOut(BaseModel):
    id: str
    ok: bool
    message: str

