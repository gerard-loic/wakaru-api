import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.methods import BaseCRUDMethods
from app.exceptions import NotFoundError
from custom.libs.knowledge_gating import mastered_corrects


class User_KnowledgeMethods(BaseCRUDMethods):

    def answer(self, db: Session, item_id: Any, user_id: int, success: bool) -> Any:
        """Enregistre une réponse de l'utilisateur `user_id` sur sa connaissance
        `item_id` : incrémente `corrects` (succès) ou `mistakes` (échec) et passe
        `is_new` à False. 404 si la ligne n'existe pas, est supprimée ou appartient
        à un autre utilisateur."""
        uk = self.model.python_class
        obj = self._get_owned(db, item_id, user_id)

        counter = "corrects" if success else "mistakes"
        # Incrément côté SQL : pas de perte si deux réponses arrivent en même temps.
        setattr(obj, counter, func.coalesce(getattr(uk, counter), 0) + 1)
        obj.is_new = False
        db.commit()
        return self.get(db, item_id)

    def read(self, db: Session, item_id: Any, user_id: int) -> Any:
        """Marque la connaissance `item_id` de `user_id` comme lue : passe `is_new` à
        False sans toucher aux compteurs, pour les éléments qui se consultent sans
        exercice (règles de grammaire). 404 si la ligne n'existe pas, est supprimée
        ou appartient à un autre utilisateur."""
        obj = self._get_owned(db, item_id, user_id)
        obj.is_new = False
        db.commit()
        return self.get(db, item_id)

    def master(self, db: Session, item_id: Any, user_id: int) -> Any:
        """Passe directement la connaissance `item_id` de `user_id` en "maitrise" :
        complète `corrects` juste assez pour atteindre les seuils (`mistakes` est
        conservé) et passe `is_new` à False. Sans effet sur les compteurs si elle est
        déjà maîtrisée. 404 si la ligne n'existe pas, est supprimée ou appartient à un
        autre utilisateur."""
        # Verrou : `corrects` est calculé à partir des compteurs lus, une réponse
        # simultanée serait sinon écrasée.
        obj = self._get_owned(db, item_id, user_id, lock=True)
        obj.corrects = mastered_corrects(obj.mistakes or 0, obj.corrects or 0)
        obj.is_new = False
        db.commit()
        return self.get(db, item_id)

    def done(self, db: Session, item_id: Any, user_id: int, day: str, index: int) -> Any:
        """Marque comme fait l'exercice n°`index` (à partir de 0) du jour `day` dans le
        programme stocké dans `details`. 404 si la ligne n'appartient pas à `user_id`,
        ou si elle n'a pas de programme ou pas d'exercice à cette position."""
        # Verrou : `details` est réécrit en entier, deux appels simultanés
        # perdraient sinon l'une des deux mises à jour.
        obj = self._get_owned(db, item_id, user_id, lock=True)

        program = json.loads(obj.details) if obj.details else {}
        exercises = program.get(day, [])
        if index >= len(exercises):
            raise NotFoundError("exercice du programme", f"{day}/{index}")

        exercises[index]["done"] = True
        obj.details = json.dumps(program, ensure_ascii=False)
        db.commit()
        return self.get(db, item_id)

    def _get_owned(self, db: Session, item_id: Any, user_id: int, lock: bool = False) -> Any:
        """Retourne la ligne `item_id` de `user_id`, 404 si elle n'existe pas, est
        supprimée ou appartient à un autre utilisateur."""
        uk = self.model.python_class
        query = db.query(uk).filter(self.model.pk_column == item_id, uk.user_id == user_id, self._not_deleted())
        if lock:
            query = query.with_for_update()
        obj = query.first()
        if obj is None:
            raise NotFoundError(self.model.name, item_id)
        return obj
