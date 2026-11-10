"""Active le dernier thème créé pour les utilisateurs non supprimés du rôle `USER` :
1. renseigne `publicated_at` (sauf s'il l'est déjà) ;
2. crée leurs `user_knowledge` sur le thème et son contenu, et leur programme, sauf
   pour ceux en mode vacances (`is_onvacation`) ;
3. envoie l'annonce (gabarit `new_theme`) à ceux qui acceptent les mails
   (`is_mailing_allowed`) ; les autres reçoivent quand même le thème à l'étape 2.
   Ceux en vacances reçoivent l'annonce avec un lien pour se remettre en actif et
   activer le thème (POST /users/resume, voir `custom/libs/vacationhelper.py`).

Les étapes 1 et 2 sont validées ensemble, avant le premier envoi.

Un email individuel est envoyé à chacun. Un échec n'interrompt pas l'envoi, et les
adresses ayant déjà reçu cette annonce (table `sendmails`, même destinataire et même
sujet) sont ignorées. Relancer la commande ne renvoie donc qu'aux adresses en échec,
sans changer la date de publication ni la progression des utilisateurs.

Usage:
    ./cmd.sh activate_new_theme --dry-run
    ./cmd.sh activate_new_theme --test-to moi@exemple.fr
    ./cmd.sh activate_new_theme --test-to moi@exemple.fr --test-vacation
    ./cmd.sh activate_new_theme
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Active le dernier thème créé pour les utilisateurs du rôle USER et le leur annonce."
    )
    parser.add_argument(
        "--test-to",
        metavar="EMAIL",
        help="N'active rien et envoie uniquement à cette adresse, qui sera ignorée lors de l'envoi réel.",
    )
    parser.add_argument(
        "--test-vacation",
        action="store_true",
        help="Avec --test-to : envoie la version destinée aux utilisateurs en vacances (lien factice).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne modifie rien et n'envoie aucun email : affiche seulement ce qui serait fait.",
    )
    args = parser.parse_args()
    if args.test_vacation and not args.test_to:
        parser.error("--test-vacation s'utilise avec --test-to.")
    return args


def main() -> None:
    args = parse_args()

    from sqlalchemy import func, select, update

    from app.crud.mapper import get_association_table
    from app.crud.model import get_model
    from app.database import SessionLocal
    from app.exceptions import ApiError
    from app.mail.service import _env, get_mail_service
    from app.main import app  # noqa: F401  (déclenche le mapping ORM et `custom.setup`)
    from custom.entities.user.methods import USER_ROLE_UID, UserMethods
    from custom.libs.llmhelper import themeMailContext
    from custom.libs.unsubscribehelper import create_unsubscribe_url
    from custom.libs.vacationhelper import create_resume_url, vacation_settings

    db = SessionLocal()
    try:
        themes = get_model("theme").table
        theme = db.execute(
            select(themes)
            .where(themes.c.deleted_at.is_(None))
            .order_by(themes.c.created_at.desc(), themes.c.id.desc())
            .limit(1)
        ).first()
        if theme is None:
            raise SystemExit("Aucun thème à activer.")

        context = themeMailContext(theme)
        subject = _env.get_template("new_theme/subject.j2").render(**context).strip()

        if args.test_to:
            users = []
            extra = {"name": "Test", "unsubscribe_url": None, "on_vacation": args.test_vacation}
            if args.test_vacation:
                extra["resume_url"] = f"{vacation_settings.resume_url_prefix}test"
            recipients = [(args.test_to, extra)]
            already_sent = set()
        else:
            user_table = get_model("user").table
            roles = get_model("role").table
            user_role = get_association_table("user_role")
            users = db.execute(
                select(
                    user_table.c.id,
                    user_table.c.email,
                    user_table.c.first_name,
                    user_table.c.is_mailing_allowed,
                    user_table.c.is_onvacation,
                )
                .join(user_role, user_role.c.user_id == user_table.c.id)
                .join(roles, roles.c.id == user_role.c.role_id)
                .where(
                    user_table.c.deleted_at.is_(None),
                    roles.c.uid == USER_ROLE_UID,
                    roles.c.deleted_at.is_(None),
                )
                .distinct()
                .order_by(user_table.c.id)
            ).all()
            # Filtré ici et non dans la requête : `users` sert aussi à l'activation.
            recipients = [
                (
                    user.email,
                    {
                        "name": user.first_name,
                        "unsubscribe_url": create_unsubscribe_url(user.id),
                        "on_vacation": bool(user.is_onvacation),
                        **(
                            {"resume_url": create_resume_url(user.id, theme.id)}
                            if user.is_onvacation
                            else {}
                        ),
                    },
                )
                for user in users
                if user.is_mailing_allowed
            ]
            sendmails = get_model("sendmail").table
            already_sent = set(
                db.execute(select(sendmails.c.to).where(sendmails.c.subject == subject)).scalars()
            )

        pending = [recipient for recipient in recipients if recipient[0] not in already_sent]
        print(f"Thème        : {theme.name} (id={theme.id})")
        print(f"Publication  : {theme.publicated_at or 'à faire'}")
        print(f"Utilisateurs : {len(users)}")
        print(f"Sans mailing : {sum(not user.is_mailing_allowed for user in users)}")
        print(f"En vacances  : {sum(bool(user.is_onvacation) for user in users)} (thème non attribué)")
        print(f"Sujet        : {subject}")
        print(f"Image        : {theme.image or 'aucune'}")
        print(f"Destinataires: {len(pending)} ({len(recipients) - len(pending)} déjà servis)")

        if args.dry_run:
            print("\n--dry-run : rien n'a été modifié, aucun email envoyé.")
            return

        if not args.test_to:
            db.execute(
                update(themes)
                .where(themes.c.id == theme.id, themes.c.publicated_at.is_(None))
                .values(publicated_at=func.now())
            )
            for user in users:
                if user.is_onvacation:
                    continue
                UserMethods.grant_theme_knowledges(db, user.id, theme.id)
            db.commit()
            print("\nThème activé.")

        mail_service = get_mail_service()
        failures = 0
        for email, extra in pending:
            try:
                mail_service.send(
                    db,
                    to=email,
                    template="new_theme",
                    context={**context, **extra},
                )
            except ApiError as exc:
                failures += 1
                print(f"! Échec pour {email} : {exc.message}")

        print(f"\n{len(pending) - failures} email(s) envoyé(s), {failures} échec(s).")
        if failures:
            raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
