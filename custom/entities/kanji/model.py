from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne


@register_model
class KanjiModel(EntityModel):
    name = "kanji"
    table_name = "kanjis"
    url_prefix = "/kanjis"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        ManyToMany(
            attribute="kanji_compositions",
            target="kanji_composition",
            association_table="kanji_kanji_composition",
            local_key="kanji_id",
            remote_key="kanji_composition_id",
        ),
        ManyToMany(
            attribute="sentences",
            target="sentence",
            association_table="sentence_kanji",
            local_key="kanji_id",
            remote_key="sentence_id",
        ),
    ]
