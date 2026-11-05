"""Supprime définitivement un thème et son contenu, en une seule transaction :
- ses phrases (et leurs tokens), règles de grammaire et exercices (et leurs items) ;
- son vocabulaire (`theme_words`, `theme_kanji`) ;
- ses mots (et leurs compositions) et kanjis, sauf ceux utilisés par un autre thème ;
- les `user_knowledge` de tout ce qui est supprimé.

La suppression est physique et non logique : une ligne marquée `deleted_at` garderait
son `uid` (unique sur `grammar_rules`) et bloquerait le ré-import du thème.

Les tokens de phrases d'autres thèmes qui pointaient vers un mot supprimé gardent leur
`word_uid` : ils sont rattachés de nouveau si ce mot est réimporté. Il en va de même
pour les compositions d'autres mots qui contenaient un kanji supprimé.

Usage:
    ./cmd.sh delete_theme --id 12 --dry-run
    ./cmd.sh delete_theme --id 12
    ./cmd.sh delete_theme --id 12 --yes
"""

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Supprime définitivement un thème, son contenu et les user_knowledge liés."
    )
    parser.add_argument("--id", type=int, required=True, help="Id du thème à supprimer.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ne modifie rien : affiche seulement ce qui serait supprimé.",
    )
    parser.add_argument("--yes", action="store_true", help="Ne demande pas de confirmation.")
    return parser.parse_args()


def purge_theme(db: Any, theme_id: int) -> tuple[dict[str, int], dict[str, int]]:
    """Supprime le thème `theme_id` et son contenu. Retourne le nombre de lignes
    supprimées par table, et le nombre de lignes conservées car partagées. Ne commit
    pas : au caller de valider la transaction ou de l'annuler."""
    from sqlalchemy import delete, select, update

    from app.crud.mapper import get_association_table
    from app.crud.model import get_model

    themes = get_model("theme").table
    theme_words = get_model("theme_word").table
    theme_kanji = get_association_table("theme_kanji")
    words = get_model("word").table
    kanjis = get_model("kanji").table
    compositions = get_model("composition").table
    composition_kanji = get_association_table("composition_kanji")
    sentences = get_model("sentence").table
    sentence_tokens = get_model("sentence_token").table
    grammar_rules = get_model("grammar_rule").table
    exercises = get_model("exercise").table
    exercise_items = get_model("exercise_item").table
    user_knowledges = get_model("user_knowledge").table

    def child_ids(table: Any) -> list[int]:
        return list(db.scalars(select(table.c.id).where(table.c.theme_id == theme_id)))

    sentence_ids = child_ids(sentences)
    grammar_rule_ids = child_ids(grammar_rules)
    exercise_ids = child_ids(exercises)

    # Les liens supprimés logiquement comptent aussi : ils référencent toujours le mot.
    linked_word_ids = set(db.scalars(select(theme_words.c.word_id).where(theme_words.c.theme_id == theme_id)))
    shared_word_ids = set(
        db.scalars(
            select(theme_words.c.word_id).where(
                theme_words.c.word_id.in_(linked_word_ids), theme_words.c.theme_id != theme_id
            )
        )
    )
    word_ids = linked_word_ids - shared_word_ids

    linked_kanji_ids = set(db.scalars(select(theme_kanji.c.kanji_id).where(theme_kanji.c.theme_id == theme_id)))
    shared_kanji_ids = set(
        db.scalars(
            select(theme_kanji.c.kanji_id).where(
                theme_kanji.c.kanji_id.in_(linked_kanji_ids), theme_kanji.c.theme_id != theme_id
            )
        )
    )
    kanji_ids = linked_kanji_ids - shared_kanji_ids

    composition_ids = list(db.scalars(select(compositions.c.id).where(compositions.c.word_id.in_(word_ids))))

    deleted: dict[str, int] = {}

    def run(label: str, statement: Any) -> None:
        deleted[label] = deleted.get(label, 0) + db.execute(statement).rowcount

    # Aucune clé étrangère n'est en cascade : les enfants passent avant leurs parents.
    knowledge_ids = {
        "theme": [theme_id],
        "sentence": sentence_ids,
        "grammar_rule": grammar_rule_ids,
        "exercise": exercise_ids,
        "word": word_ids,
        "kanji": kanji_ids,
    }
    for entity_name, entity_ids in knowledge_ids.items():
        run(
            "user_knowledges",
            delete(user_knowledges).where(
                user_knowledges.c.entity_name == entity_name, user_knowledges.c.entity_id.in_(entity_ids)
            ),
        )

    run("sentence_tokens", delete(sentence_tokens).where(sentence_tokens.c.sentence_id.in_(sentence_ids)))
    run("sentences", delete(sentences).where(sentences.c.id.in_(sentence_ids)))
    run("grammar_rules", delete(grammar_rules).where(grammar_rules.c.id.in_(grammar_rule_ids)))
    run("exercise_items", delete(exercise_items).where(exercise_items.c.exercise_id.in_(exercise_ids)))
    run("exercises", delete(exercises).where(exercises.c.id.in_(exercise_ids)))
    run("theme_words", delete(theme_words).where(theme_words.c.theme_id == theme_id))
    run("theme_kanji", delete(theme_kanji).where(theme_kanji.c.theme_id == theme_id))
    run(
        "composition_kanji",
        delete(composition_kanji).where(
            composition_kanji.c.composition_id.in_(composition_ids) | composition_kanji.c.kanji_id.in_(kanji_ids)
        ),
    )
    run("compositions", delete(compositions).where(compositions.c.id.in_(composition_ids)))
    run(
        "sentence_tokens détachés (autres thèmes)",
        update(sentence_tokens).where(sentence_tokens.c.word_id.in_(word_ids)).values(word_id=None),
    )
    run("words", delete(words).where(words.c.id.in_(word_ids)))
    run("kanjis", delete(kanjis).where(kanjis.c.id.in_(kanji_ids)))
    run("themes", delete(themes).where(themes.c.id == theme_id))

    return deleted, {"words": len(shared_word_ids), "kanjis": len(shared_kanji_ids)}


def main() -> None:
    args = parse_args()

    from sqlalchemy import select

    from app.crud.model import get_model
    from app.database import SessionLocal
    from app.main import app  # noqa: F401  (déclenche le mapping ORM et `custom.setup`)

    db = SessionLocal()
    try:
        themes = get_model("theme").table
        theme = db.execute(select(themes).where(themes.c.id == args.id)).first()
        if theme is None:
            raise SystemExit(f"Aucun thème avec l'id {args.id}.")

        # Aperçu exact : la suppression est jouée puis annulée.
        deleted, kept = purge_theme(db, theme.id)
        db.rollback()

        print(f"Thème        : {theme.name} (id={theme.id})")
        print(f"Publication  : {theme.publicated_at or 'non publié'}")
        print("\nLignes concernées :")
        for label, count in deleted.items():
            print(f"  {label:<42}: {count}")
        print("\nConservés car utilisés par un autre thème :")
        for label, count in kept.items():
            print(f"  {label:<42}: {count}")
        if theme.image:
            print(f"\nImage conservée : {theme.image}")

        if args.dry_run:
            print("\n--dry-run : rien n'a été modifié.")
            return

        if not args.yes:
            try:
                answer = input(f"\nSuppression définitive. Saisir l'id du thème ({theme.id}) pour confirmer : ")
            except EOFError:
                raise SystemExit("\nConfirmation impossible sans terminal : relancer avec --yes.")
            if answer.strip() != str(theme.id):
                raise SystemExit("Abandon : rien n'a été modifié.")

        purge_theme(db, theme.id)
        db.commit()
        print(f"\nThème {theme.id} supprimé.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
