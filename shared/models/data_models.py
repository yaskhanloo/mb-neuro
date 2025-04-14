from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

@dataclass
class BaseEntity:
    """Base class for all data models"""
    id: Optional[int] = None

@dataclass
class Patient(BaseEntity):
    """Patient data model"""
    fid: Optional[int] = None
    ssr: Optional[int] = None
    name_last: Optional[str] = None
    name_first: Optional[str] = None
    birth_date: Optional[datetime] = None
    sex: Optional[str] = None
    non_swiss: Optional[bool] = None
    zip: Optional[str] = None
    
@dataclass
class MappingField:
    """Represents a field mapping between EPIC and secuTrial"""
    epic_column_name: str
    epic_type: str
    epic_file_name: str
    secuTrial_column_name: str
    secuTrial_type: str
    secuTrial_file_name: str
    value_mapping: Optional[Dict[Any, Any]] = None