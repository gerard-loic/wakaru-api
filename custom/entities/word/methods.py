from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.methods import BaseCRUDMethods
from app.crud.model import get_model
from custom.libs.conjugation import conjugate


class WordMethods(BaseCRUDMethods):
    def detail_extra(self, db: Session, word) -> dict:
        """Champs calculés de `GET /words/{id}` : `conjugation` vaut `None` hors verbes.
        Le `uid` est lu à part : accéder à `word.partofspeech` chargerait la relation,
        qui apparaîtrait alors dans la réponse sans avoir été demandée via `with`."""
        partofspeeches = get_model("partofspeeche").table.c
        pos_uid = db.scalar(select(partofspeeches.uid).where(partofspeeches.id == word.partofspeech_id))
        return {"conjugation": conjugate(word.writing, word.reading, pos_uid)}
