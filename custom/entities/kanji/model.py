from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne, OneToMany


@register_model
class KanjiModel(EntityModel):
    name = "kanji"
    table_name = "kanjis"
    url_prefix = "/kanjis"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToMany(
            attribute="compositions",
            target="composition",
            association_table="composition_kanji",
            local_key="kanji_id",
            remote_key="composition_id",
        ),
        ManyToMany(
            attribute="themes",
            target="theme",
            association_table="theme_kanji",
            local_key="kanji_id",
            remote_key="theme_id",
        ),
    ]
