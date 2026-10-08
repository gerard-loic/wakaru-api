from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.crud.mapper import get_association_table
from app.crud.model import EntityModel, get_all_models


def resolve_model(table: str) -> type[EntityModel]:
    """Retrouve le modèle Sylo à partir de son nom d'entité (`theme`) ou de sa
    table (`themes`)."""
    models = get_all_models()
    if table in models:
        return models[table]
    for model in models.values():
        if model.table_name == table:
            return model
    raise ValueError(f"Aucune entité ou table nommée '{table}'.")


class ModelHelper:
    """Méthodes génériques d'interaction avec la BDD, sur n'importe quelle
    entité Sylo (désignée par son nom d'entité ou sa table).

    Aucune méthode ne commit : les lignes sont seulement flushées, au caller de
    valider la transaction (ou de la rollback si la suite échoue)."""

    def __init__(self, db: Session):
        self._db = db

    def get(self, table: str, attribute: str, value: Any, multiple: bool = False) -> Any | list[Any] | None:
        """Cherche les lignes de `table` dont `attribute` vaut `value`
        (insensible à la casse pour les chaînes, lignes supprimées exclues si la
        table a une colonne `deleted_at`).

        Si `multiple` est False, retourne l'id de la première ligne trouvée, ou
        None. Si `multiple` est True, retourne la liste de tous les ids (vide si
        aucune ligne ne correspond)."""
        model = resolve_model(table)
        python_class = model.python_class
        if attribute not in model.table.c:
            raise ValueError(f"La table '{model.table_name}' n'a pas de colonne '{attribute}'.")

        column = getattr(python_class, attribute)
        if isinstance(value, str):
            condition = func.lower(column) == value.lower()
        else:
            condition = column == value

        query = select(model.pk_column).where(condition)
        if hasattr(python_class, "deleted_at"):
            query = query.where(python_class.deleted_at.is_(None))
        if multiple:
            return list(self._db.execute(query).scalars().all())

        return self._db.execute(query.limit(1)).scalar_one_or_none()

    def getOrCreate(self, table: str, attribute: str, value: Any, data: dict | None = None) -> tuple[Any, bool]:
        """Retourne un tuple `(id, created)` pour la ligne de `table` dont
        `attribute` vaut `value` (insensible à la casse pour les chaînes,
        lignes supprimées exclues). Si elle n'existe pas, la crée avec `data`
        (complété par `attribute: value`). `created` vaut True si la ligne a
        été créée, False si elle existait déjà."""
        existing_id = self.get(table, attribute, value)
        if existing_id is not None:
            return existing_id, False

        return self.create(table, {**(data or {}), attribute: value}), True

    def create(self, table: str, data: dict) -> Any:
        """Crée une ligne dans `table` avec `data` et retourne son id, sans
        vérifier qu'une ligne équivalente existe déjà."""
        model = resolve_model(table)
        obj = model.python_class(**data)
        self._db.add(obj)
        self._db.flush()
        return getattr(obj, model.pk_name())

    def update(self, table: str, id: Any, data: dict) -> None:
        """Met à jour la ligne de `table` dont l'id vaut `id` avec les valeurs
        de `data`. Lève une ValueError si la ligne n'existe pas (ou est
        supprimée) ou si une clé de `data` n'est pas une colonne de la table."""
        model = resolve_model(table)
        python_class = model.python_class
        for attribute in data:
            if attribute not in model.table.c:
                raise ValueError(f"La table '{model.table_name}' n'a pas de colonne '{attribute}'.")

        obj = self._db.get(python_class, id)
        if obj is None or getattr(obj, "deleted_at", None) is not None:
            raise ValueError(f"Aucune ligne d'id {id} dans la table '{model.table_name}'.")

        for attribute, value in data.items():
            setattr(obj, attribute, value)
        self._db.flush()

    def link(self, table: str, data: dict) -> None:
        """Insère une ligne dans la table d'association `table` (relation
        ManyToMany, ex. `theme_word`), qui n'est pas une entité Sylo."""
        self._db.execute(insert(get_association_table(table)).values(**data))

    def initUsers(self, entity_name: str, entity_id: Any, level_id: Any) -> list:
        """Crée une ligne dans `user_knowledges` pour l'élément (`entity_name`,
        `entity_id`) et chaque utilisateur de niveau `level_id` (utilisateurs
        supprimés exclus). Retourne les ids créés.

        `entity_name` accepte le nom d'entité (`word`) ou la table (`words`) ;
        c'est le nom d'entité qui est stocké, comme attendu par
        `knowledge_gating`."""
        entity_name = resolve_model(entity_name).name
        user_model = resolve_model("user")
        user_class = user_model.python_class

        user_ids = self._db.execute(
            select(user_model.pk_column).where(
                user_class.level_id == level_id,
                user_class.deleted_at.is_(None),
            )
        ).scalars().all()

        out = []
        for user_id in user_ids:
            out.append(self.create(
                table="user_knowledges",
                data={
                    "is_new" : True,
                    "mistakes" : 0,
                    "corrects" : 0,
                    "user_id" : user_id,
                    "entity_name" : entity_name,
                    "entity_id" : entity_id
                }
            ))

        return out
