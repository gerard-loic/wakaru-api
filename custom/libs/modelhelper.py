from typing import Any

from sqlalchemy import and_, func, inspect, insert, select
from sqlalchemy.orm import Session, selectinload

from app.crud.mapper import get_association_table
from app.crud.model import EntityModel, get_all_models
from app.responses import serialize
from custom.libs.knowledge_gating import _serialize_knowledge, knowledge_type_conditions


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


def _value_condition(column: Any, value: Any) -> Any:
    """Condition `column == value` (insensible à la casse pour les chaînes), ou
    `column IN value` si `value` est une liste."""
    if isinstance(value, (list, tuple, set)):
        values = list(value)
        if values and all(isinstance(v, str) for v in values):
            return func.lower(column).in_([v.lower() for v in values])
        return column.in_(values)
    if isinstance(value, str):
        return func.lower(column) == value.lower()
    return column == value


def _path_condition(python_class: Any, path: str, value: Any) -> Any:
    """Condition sur `path`, un attribut de `python_class` (`reading`) ou un
    attribut d'une relation, éventuellement imbriquée (`level.name`,
    `themes.name`, `compositions.kanjis.writing`). Les lignes liées supprimées
    (colonne `deleted_at`) sont ignorées."""
    name, _, rest = path.partition(".")
    mapper = inspect(python_class)
    if not rest:
        if name not in mapper.columns:
            raise ValueError(f"'{python_class.__name__}' n'a pas de colonne '{name}'.")
        return _value_condition(getattr(python_class, name), value)

    if name not in mapper.relationships:
        raise ValueError(f"'{python_class.__name__}' n'a pas de relation '{name}'.")
    relation = mapper.relationships[name]
    target_class = relation.mapper.class_
    condition = _path_condition(target_class, rest, value)
    if hasattr(target_class, "deleted_at"):
        condition = condition & target_class.deleted_at.is_(None)

    attribute = getattr(python_class, name)
    return attribute.any(condition) if relation.uselist else attribute.has(condition)


def _load_option(python_class: Any, path: str) -> Any:
    """Option `selectinload` pour la relation `path`, éventuellement imbriquée
    (`compositions.kanjis`)."""
    option = None
    for name in path.split("."):
        mapper = inspect(python_class)
        if name not in mapper.relationships:
            raise ValueError(f"'{python_class.__name__}' n'a pas de relation '{name}'.")
        attribute = getattr(python_class, name)
        option = selectinload(attribute) if option is None else option.selectinload(attribute)
        python_class = mapper.relationships[name].mapper.class_
    return option


class ModelHelper:
    """Méthodes génériques d'interaction avec la BDD, sur n'importe quelle
    entité Sylo (désignée par son nom d'entité ou sa table).

    Aucune méthode ne commit : les lignes sont seulement flushées, au caller de
    valider la transaction (ou de la rollback si la suite échoue)."""

    def __init__(self, db: Session):
        self._db = db

    def get(self, table: str, attribute: str, value: Any, multiple: bool = False, contains: bool = False) -> Any | list[Any] | None:
        """Cherche les lignes de `table` dont `attribute` vaut `value`
        (insensible à la casse pour les chaînes, lignes supprimées exclues si la
        table a une colonne `deleted_at`).

        Si `contains` est True, `value` (une chaîne) doit seulement être
        contenue dans `attribute` (ex. "A" trouve "123ABC").

        Si `multiple` est False, retourne l'id de la première ligne trouvée, ou
        None. Si `multiple` est True, retourne la liste de tous les ids (vide si
        aucune ligne ne correspond)."""
        model = resolve_model(table)
        python_class = model.python_class
        if attribute not in model.table.c:
            raise ValueError(f"La table '{model.table_name}' n'a pas de colonne '{attribute}'.")

        column = getattr(python_class, attribute)
        if contains:
            if not isinstance(value, str):
                raise ValueError("`contains` n'est utilisable qu'avec une valeur de type chaîne.")
            condition = func.lower(column).contains(value.lower(), autoescape=True)
        elif isinstance(value, str):
            condition = func.lower(column) == value.lower()
        else:
            condition = column == value

        query = select(model.pk_column).where(condition)
        if hasattr(python_class, "deleted_at"):
            query = query.where(python_class.deleted_at.is_(None))
        if multiple:
            return list(self._db.execute(query).scalars().all())

        return self._db.execute(query.limit(1)).scalar_one_or_none()

    def count(self, table: str, user_id: Any | None = None, only_new: bool = False) -> int:
        """Retourne le nombre de lignes de `table` (lignes supprimées exclues si
        la table a une colonne `deleted_at`).

        Si `user_id` est fourni, ne compte que les lignes liées à cet
        utilisateur dans `user_knowledges` (même règle que `knowledge_gating`,
        sans tenir compte de la permission KNOWLEDGE_UNLIMITED). Si `only_new`
        est True, seules les liaisons avec `is_new` à True sont retenues
        (nécessite `user_id`)."""
        if only_new and user_id is None:
            raise ValueError("`only_new` nécessite un `user_id`.")

        model = resolve_model(table)
        python_class = model.python_class

        query = select(func.count()).select_from(model.table)
        if hasattr(python_class, "deleted_at"):
            query = query.where(python_class.deleted_at.is_(None))
        if user_id is not None:
            uk = resolve_model("user_knowledge").table.c
            known_ids = select(uk.entity_id).where(
                uk.entity_name == model.name,
                uk.user_id == user_id,
                uk.deleted_at.is_(None),
            )
            if only_new:
                known_ids = known_ids.where(uk.is_new.is_(True))
            query = query.where(model.pk_column.in_(known_ids))

        return self._db.execute(query).scalar_one()

    def getRandom(
        self,
        table: str,
        user_id: Any,
        focus: str = "random",
        avoid_ids: list | None = None,
        load: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict | None:
        """Retourne une ligne de `table` tirée au hasard (sérialisée en dict avec
        toutes ses colonnes), ou None si aucune ne correspond. Seules les lignes
        liées à `user_id` dans `user_knowledges` sont candidates (lignes
        supprimées exclues si la table a une colonne `deleted_at`). La ligne
        `user_knowledge` correspondante est ajoutée sous la clé
        `user_knowledge` (sérialisée avec son `type`, comme dans
        `knowledge_gating`).

        `focus` :
        - "random" : n'importe quelle ligne connue de l'utilisateur ;
        - "weakness" : seulement les lignes dont le `user_knowledge` est
          "arevoir" (même règle que `knowledge_gating`) ;
        - "theme" : seulement les lignes rattachées au thème de la semaine de
          l'utilisateur (dernier thème créé parmi ceux qu'il connaît).

        Les lignes dont l'id figure dans `avoid_ids` ne sont jamais choisies.

        `load` : relations à charger et inclure dans le résultat, imbriquées
        avec un point (ex. `["level", "compositions.kanjis"]`).

        `filters` : conditions que la ligne doit toutes respecter, la clé étant
        un attribut de l'élément (`"reading"`) ou d'une relation, imbriquée
        avec un point (`"level.name"`, `"themes.name"`). La valeur est comparée
        par égalité (insensible à la casse pour les chaînes) ou, si c'est une
        liste, par appartenance. Pour une relation multiple, il suffit qu'une
        des lignes liées corresponde."""
        model = resolve_model(table)
        python_class = model.python_class
        query = self._knownQuery(table, user_id, focus, filters)
        if avoid_ids:
            query = query.where(model.pk_column.not_in(avoid_ids))
        for path in load or []:
            query = query.options(_load_option(python_class, path))

        row = self._db.execute(query.order_by(func.random()).limit(1)).one_or_none()
        if row is None:
            return None
        obj, knowledge = row
        return {**serialize(obj), "user_knowledge": _serialize_knowledge(knowledge)}

    def getKnown(
        self,
        table: str,
        user_id: Any,
        focus: str = "random",
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Retourne toutes les lignes de `table` que `getRandom` pourrait tirer
        pour `user_id` avec ce `focus` et ces `filters`."""
        query = self._knownQuery(table, user_id, focus, filters)
        return list(self._db.execute(query).scalars().all())

    def countKnown(
        self,
        table: str,
        user_id: Any,
        focus: str = "random",
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Retourne le nombre de lignes de `table` que `getRandom` pourrait
        tirer pour `user_id` avec ce `focus` et ces `filters`."""
        model = resolve_model(table)
        query = self._knownQuery(table, user_id, focus, filters)
        query = query.with_only_columns(func.count(model.pk_column), maintain_column_froms=True)
        return self._db.execute(query).scalar_one()

    def knowledgeProportions(self, table: str, user_id: Any, filters: dict[str, Any] | None = None) -> dict[str, float]:
        """Retourne la répartition en pourcentage (arrondie à une décimale) des
        lignes de `table` connues de `user_id` selon leur type de maîtrise :
        `aucun` (nouveau), `encours`, `maitrise` et `arevoir` (même règle que
        `knowledge_gating`). Tout vaut 0 si l'utilisateur ne connaît aucune ligne.
        `filters` : voir `getRandom`."""
        query = self._knownQuery(table, user_id, "random", filters).with_only_columns(
            *(func.count().filter(condition).label(type_) for type_, condition in knowledge_type_conditions().items()),
            maintain_column_froms=True,
        )
        counts = self._db.execute(query).one()._asdict()
        total = sum(counts.values())
        return {type_: round(count * 100 / total, 1) if total else 0.0 for type_, count in counts.items()}

    def _knownQuery(self, table: str, user_id: Any, focus: str, filters: dict[str, Any] | None) -> Any:
        """Requête des lignes de `table` liées à `user_id` dans
        `user_knowledges`, restreintes par `focus` et `filters` (voir
        `getRandom`). Sélectionne la ligne et son `user_knowledge`."""
        if focus not in ("random", "weakness", "theme"):
            raise ValueError(f"Focus '{focus}' non supporté.")

        model = resolve_model(table)
        python_class = model.python_class
        uk_class = resolve_model("user_knowledge").python_class
        query = select(python_class, uk_class).join(uk_class, and_(
            uk_class.entity_id == model.pk_column,
            uk_class.entity_name == model.name,
            uk_class.user_id == user_id,
            uk_class.deleted_at.is_(None),
        ))
        if focus == "weakness":
            query = query.where(knowledge_type_conditions()["arevoir"])
        if focus == "theme":
            query = query.where(model.pk_column.in_(self._themeIdsQuery(model, user_id)))
        if hasattr(python_class, "deleted_at"):
            query = query.where(python_class.deleted_at.is_(None))
        for path, value in (filters or {}).items():
            query = query.where(_path_condition(python_class, path, value))
        return query

    def _currentThemeId(self, user_id: Any) -> Any | None:
        """Id du thème de la semaine de `user_id` : le dernier thème créé parmi
        ceux qu'il connaît (lien dans `user_knowledges`), ou None."""
        theme = resolve_model("theme")
        uk_table = resolve_model("user_knowledge").table
        uk = uk_table.c
        query = (
            select(theme.pk_column)
            .join(uk_table, and_(
                uk.entity_id == theme.pk_column,
                uk.entity_name == theme.name,
                uk.user_id == user_id,
                uk.deleted_at.is_(None),
            ))
            .where(theme.table.c.deleted_at.is_(None))
            .order_by(theme.table.c.created_at.desc(), theme.pk_column.desc())
            .limit(1)
        )
        return self._db.execute(query).scalar()

    def _themeIdsQuery(self, model: type[EntityModel], user_id: Any) -> Any:
        """SELECT des ids de `model` rattachés au thème de la semaine de
        `user_id` (colonne `theme_id`, table `theme_words` ou `theme_kanji`)."""
        theme_id = self._currentThemeId(user_id)
        if "theme_id" in model.table.c:
            return select(model.pk_column).where(model.table.c.theme_id == theme_id)
        if model.name == "word":
            theme_word = resolve_model("theme_word").table.c
            return select(theme_word.word_id).where(
                theme_word.theme_id == theme_id, theme_word.deleted_at.is_(None)
            )
        if model.name == "kanji":
            theme_kanji = get_association_table("theme_kanji").c
            return select(theme_kanji.kanji_id).where(theme_kanji.theme_id == theme_id)
        raise ValueError(f"Le focus 'theme' n'est pas supporté pour '{model.name}'.")

    def getOrCreate(self,table: str, attribute: str, value: Any, data: dict | None = None) -> tuple[Any, bool]:
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

    def link(self, table: str, data: dict) -> bool:
        """Insère une ligne dans la table d'association `table` (relation
        ManyToMany, ex. `theme_word`), qui n'est pas une entité Sylo, si elle
        n'existe pas déjà. Retourne True si la ligne a été créée, False si elle
        existait déjà."""
        association = get_association_table(table)
        exists = self._db.execute(
            select(1).select_from(association).where(
                *(association.c[column] == value for column, value in data.items())
            ).limit(1)
        ).first()
        if exists is not None:
            return False

        self._db.execute(insert(association).values(**data))
        return True

    def initUsers(self, entity_name: str, entity_id: Any, level_id: Any, role_uid: str) -> list:
        """Crée une ligne dans `user_knowledges` pour l'élément (`entity_name`,
        `entity_id`) et chaque utilisateur de niveau `level_id` ayant le rôle
        `role_uid` (utilisateurs supprimés exclus), sauf s'il en a déjà une : un mot ou un kanji repris
        par une nouvelle leçon garde ainsi sa progression. Retourne les ids créés.

        `entity_name` accepte le nom d'entité (`word`) ou la table (`words`) ;
        c'est le nom d'entité qui est stocké, comme attendu par
        `knowledge_gating`."""
        entity_name = resolve_model(entity_name).name
        user_model = resolve_model("user")
        user_class = user_model.python_class
        uk = resolve_model("user_knowledge").table.c
        role = resolve_model("role").table
        user_role = get_association_table("user_role")

        known_user_ids = select(uk.user_id).where(
            uk.entity_name == entity_name,
            uk.entity_id == entity_id,
            uk.deleted_at.is_(None),
        )
        user_ids = self._db.execute(
            select(user_model.pk_column)
            .join(user_role, user_role.c.user_id == user_model.pk_column)
            .join(role, role.c.id == user_role.c.role_id)
            .where(
                user_class.level_id == level_id,
                user_class.deleted_at.is_(None),
                role.c.uid == role_uid,
                role.c.deleted_at.is_(None),
                user_model.pk_column.not_in(known_user_ids),
            )
            .distinct()
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
