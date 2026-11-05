# Surcharge de l'entité user du core : `create` et `login` changent (voir methods.py),
# le modèle est repris en ajoutant la relation vers `level` (colonne `level_id`).
from app.crud.model import register_model
from app.crud.relationships import ManyToOne
from app.entities.user.model import UserModel as CoreUserModel


@register_model
class UserModel(CoreUserModel):
    relationships = [
        *CoreUserModel.relationships,
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
    ]
