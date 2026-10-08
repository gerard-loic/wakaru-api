from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany


@register_model
class KanjiwordModel(EntityModel):
    name = "kanjiword"
    table_name = "kanjiwords"
    url_prefix = "/kanjiwords"
    relationships = [
        ManyToMany(
            attribute="kanjis",
            target="kanji",
            association_table="kanji_compositions",
            local_key="kanjiword_id",
            remote_key="kanji_id",
        ),
    ]
