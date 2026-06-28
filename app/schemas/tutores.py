from pydantic import BaseModel

class TutorIn(BaseModel):
   nombreCompleto: str
   telefono: str
