import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy import delete, insert, literal, select, update
from sqlalchemy.orm import Session

from app.crud.mapper import get_association_table
from app.crud.model import get_model
from app.database import SessionLocal
from app.entities.user.methods import UserMethods as CoreUserMethods
from app.exceptions import ApiError, ConflictError, ForbiddenError
from app.mail.service import get_mail_service
from app.security import verify_password
from custom.libs.passwordresethelper import (
    InvalidResetTokenError,
    check_reset_token,
    create_reset_token,
    password_reset_settings,
    read_reset_token_user_id,
)
from custom.libs.traininghelper import TrainingHelper
from custom.libs.unsubscribehelper import read_unsubscribe_token

logger = logging.getLogger("sylo_api")

# Rôle des apprenants : à la création, ils reçoivent d'office une connaissance
# sur chaque hiragana et katakana, ainsi que sur le dernier thème publié et son
# contenu (vocabulaire, kanjis, phrases, exercices, règles de grammaire).
USER_ROLE_UID = "USER"
DEFAULT_KNOWLEDGE_ENTITIES = ("hiragana", "katakana")
# Entités rattachées directement au thème par une colonne `theme_id`.
THEME_CHILD_ENTITIES = ("sentence", "exercise", "grammar_rule")


class UserMethods(CoreUserMethods):

    def create(self, db: Session, data: dict, with_: Iterable[str] = ()):
        """Comme le create du core ; si l'utilisateur a le rôle `USER`, on lui crée
        en plus une ligne `user_knowledge` sur chaque hiragana et katakana, et sur
        le dernier thème publié avec tout son contenu."""
        user = super().create(db, data, with_=with_)
        if self._has_role(db, user.id, USER_ROLE_UID):
            self._grant_default_knowledges(db, user.id)
        return user

    def register(self, db: Session, data: dict, with_: Iterable[str] = ()):
        """Inscription publique (POST /users/register) : le rôle `USER` et le niveau
        par défaut sont imposés ici, le front ne peut pas les choisir."""
        email = data["email"].strip().lower()
        # Contrainte unique sur l'email, y compris pour les comptes supprimés.
        user_cls = self.model.python_class
        if db.query(user_cls.id).filter(user_cls.email == email).first() is not None:
            raise ConflictError("Un compte existe déjà avec cet email.")

        role = get_model("role").table
        role_id = db.execute(
            select(role.c.id).where(role.c.uid == USER_ROLE_UID, role.c.deleted_at.is_(None))
        ).scalar()
        level = get_model("level").table
        level_id = db.execute(
            select(level.c.id)
            .where(level.c.is_default.is_(True), level.c.deleted_at.is_(None))
            .limit(1)
        ).scalar()
        if role_id is None or level_id is None:
            raise ApiError("Rôle USER ou niveau par défaut introuvable.")

        return self.create(
            db, {**data, "email": email, "roles": [role_id], "level_id": level_id}, with_=with_
        )

    def update_me(self, db: Session, user_id: int, data: dict, with_: Iterable[str] = ()):
        """Modification de son propre compte (PUT /users/me). L'email servant de login,
        changer l'email ou le mot de passe exige le mot de passe actuel : un token volé
        ne suffit pas à s'approprier le compte."""
        data = dict(data)
        current_password = data.pop("current_password", None)
        user = self.get_or_404(db, user_id)

        if "email" in data:
            data["email"] = data["email"].strip().lower()
            if data["email"] == user.email:
                del data["email"]

        if "email" in data or "password" in data:
            if (
                not current_password
                or not user.password
                or not verify_password(current_password, user.password)
            ):
                raise ForbiddenError("Mot de passe actuel incorrect.")

        if "email" in data:
            # Contrainte unique sur l'email, y compris pour les comptes supprimés.
            user_cls = self.model.python_class
            taken = db.query(user_cls.id).filter(
                user_cls.email == data["email"], user_cls.id != user_id
            )
            if taken.first() is not None:
                raise ConflictError("Un compte existe déjà avec cet email.")

        return self.update(db, user_id, data, with_=with_)

    def send_password_reset(self, email: str) -> None:
        """Envoie le mail de réinitialisation si un compte correspond à `email`. Lancée
        en tâche de fond par POST /users/forgot-password, avec sa propre session : ni
        la réponse ni son délai ne révèlent si le compte existe, et un échec d'envoi
        est seulement journalisé."""
        email = email.strip().lower()
        user_cls = self.model.python_class
        try:
            with SessionLocal() as db:
                user = db.query(user_cls).filter(
                    user_cls.email == email, self._not_deleted()
                ).first()
                if user is None:
                    return
                token = create_reset_token(user)
                get_mail_service().send(
                    db,
                    to=user.email,
                    template="reset_password",
                    context={
                        "name": user.first_name,
                        "reset_url": f"{password_reset_settings.password_reset_url_prefix}{token}",
                        "ttl_minutes": password_reset_settings.password_reset_ttl_minutes,
                    },
                )
        except Exception:
            logger.exception("Échec de l'envoi du mail de réinitialisation de mot de passe.")

    def reset_password(self, db: Session, token: str, password: str) -> None:
        """Change le mot de passe à partir d'un token reçu par mail (POST
        /users/reset-password). Les sessions ouvertes sont révoquées, et une éventuelle
        invitation (`initial_token`) en attente est annulée."""
        user = self.get(db, read_reset_token_user_id(token))
        if user is None:
            raise InvalidResetTokenError()
        check_reset_token(token, user)

        user_token = get_model("usertoken").table
        db.execute(
            update(user_token)
            .where(user_token.c.user_id == user.id, user_token.c.deleted_at.is_(None))
            .values(deleted_at=datetime.utcnow())
        )
        # Le commit de `update` valide aussi la révocation des sessions.
        self.update(db, user.id, {"password": password, "initial_token": None})

    def unsubscribe(self, db: Session, token: str) -> None:
        """Coupe les emails d'information à partir du token reçu par mail (POST
        /users/unsubscribe). Un compte supprimé depuis l'envoi n'est pas une erreur :
        il ne reçoit déjà plus rien."""
        user_id = read_unsubscribe_token(token)
        if self.get(db, user_id) is not None:
            self.update(db, user_id, {"is_mailing_allowed": False})

    def delete(self, db: Session, item_id: int) -> None:
        """Comme le delete du core (suppression logique et anonymisation), avec en plus
        l'effacement définitif des `user_knowledge` : le commit du core valide les deux
        ensemble."""
        user_knowledge = get_model("user_knowledge").table
        db.execute(delete(user_knowledge).where(user_knowledge.c.user_id == item_id))
        super().delete(db, item_id)

    def login(self, db: Session, email: str, password: str) -> dict:
        """Comme le login du core, avec en plus `user_id` dans la réponse."""
        result = super().login(db, email, password)
        token_cls = get_model("usertoken").python_class
        token_row = db.query(token_cls).filter(token_cls.token == result["token"]).one()
        return {**result, "user_id": token_row.user_id}

    @staticmethod
    def _has_role(db: Session, user_id: int, role_uid: str) -> bool:
        role = get_model("role").table
        user_role = get_association_table("user_role")
        query = (
            select(role.c.id)
            .join(user_role, user_role.c.role_id == role.c.id)
            .where(user_role.c.user_id == user_id, role.c.uid == role_uid, role.c.deleted_at.is_(None))
        )
        return db.execute(query).first() is not None

    @classmethod
    def _grant_default_knowledges(cls, db: Session, user_id: int) -> None:
        for entity_name in DEFAULT_KNOWLEDGE_ENTITIES:
            entity = get_model(entity_name)
            cls._insert_knowledges(
                db, user_id, entity_name,
                select(entity.pk_column).where(entity.table.c.deleted_at.is_(None)),
            )

        theme = get_model("theme")
        theme_id = db.execute(
            select(theme.pk_column)
            .where(theme.table.c.deleted_at.is_(None), theme.table.c.publicated_at.is_not(None))
            .order_by(theme.table.c.publicated_at.desc(), theme.pk_column.desc())
            .limit(1)
        ).scalar()
        if theme_id is not None:
            cls.grant_theme_knowledges(db, user_id, theme_id)
        db.commit()

    @classmethod
    def grant_theme_knowledges(cls, db: Session, user_id: int, theme_id: int) -> None:
        """Donne à `user_id` les connaissances du thème et de tout son contenu, puis
        son programme. Les éléments déjà connus gardent leur progression : on peut
        donc rappeler la méthode sans risque. Ne commit pas."""
        cls._insert_knowledges(db, user_id, "theme", select(literal(theme_id)))

        for entity_name in THEME_CHILD_ENTITIES:
            entity = get_model(entity_name)
            cls._insert_knowledges(
                db, user_id, entity_name,
                select(entity.pk_column).where(
                    entity.table.c.theme_id == theme_id, entity.table.c.deleted_at.is_(None)
                ),
            )

        word = get_model("word")
        theme_word = get_model("theme_word").table
        cls._insert_knowledges(
            db, user_id, "word",
            select(word.pk_column)
            .join(theme_word, theme_word.c.word_id == word.pk_column)
            .where(
                theme_word.c.theme_id == theme_id,
                theme_word.c.deleted_at.is_(None),
                word.table.c.deleted_at.is_(None),
            )
            .distinct(),
        )

        kanji = get_model("kanji")
        theme_kanji = get_association_table("theme_kanji")
        cls._insert_knowledges(
            db, user_id, "kanji",
            select(kanji.pk_column)
            .join(theme_kanji, theme_kanji.c.kanji_id == kanji.pk_column)
            .where(theme_kanji.c.theme_id == theme_id, kanji.table.c.deleted_at.is_(None))
            .distinct(),
        )

        # Le programme dépend des connaissances créées ci-dessus.
        TrainingHelper.initThemeProgram(db, theme_id, user_id=user_id)

    @staticmethod
    def _insert_knowledges(db: Session, user_id: int, entity_name: str, entity_ids) -> None:
        """Crée une ligne `user_knowledge` par id renvoyé par `entity_ids` (un SELECT
        d'une seule colonne), en un seul INSERT ... SELECT sans charger les lignes.
        Les éléments que l'utilisateur connaît déjà sont ignorés."""
        user_knowledge = get_model("user_knowledge").table
        ids = entity_ids.subquery()
        (entity_id,) = ids.c
        known_ids = select(user_knowledge.c.entity_id).where(
            user_knowledge.c.user_id == user_id,
            user_knowledge.c.entity_name == entity_name,
            user_knowledge.c.deleted_at.is_(None),
        )
        rows = select(literal(user_id), literal(entity_name), entity_id).where(
            entity_id.not_in(known_ids)
        )
        db.execute(
            insert(user_knowledge).from_select(["user_id", "entity_name", "entity_id"], rows)
        )
