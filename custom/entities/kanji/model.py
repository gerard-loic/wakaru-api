from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne


@register_model
class KanjiModel(EntityModel):
    name = "kanji"
    table_name = "kanjis"
    url_prefix = "/kanjis"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToMany(
            attribute="themes",
            target="theme",
            association_table="theme_kanji",
            local_key="kanji_id",
            remote_key="theme_id",
        ),
        ManyToMany(
            attribute="kanji_compositions",
            target="kanjiword",
            association_table="kanji_compositions",
            local_key="kanji_id",
            remote_key="kanjiword_id",
        ),
        ManyToMany(
            attribute="sentences",
            target="sentence",
            association_table="sentence_kanji",
            local_key="kanji_id",
            remote_key="sentence_id",
        ),
    ]
