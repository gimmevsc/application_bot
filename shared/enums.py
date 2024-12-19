import json
from enum import Enum


class AcceptableEnum(str, Enum):
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __str__(self):
        return f"{self.value}"

    def __hash__(self):
        return hash(self.value)

#додав ще один статус max
class EUserStatus(AcceptableEnum):
    DEMO: str = "demo"
    UNLIMITED: str = "unlim"
    ADMIN: str = "admin"
    MAX: str = "max"
    
    

