from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany


@register_model
class Kanji_CompositionModel(EntityModel):
    name = "kanji_composition"
    table_name = "kanji_compositions"
    url_prefix = "/kanji_compositions"
    relationships = [
        ManyToMany(
            attribute="kanjis",
            target="kanji",
            association_table="kanji_kanji_composition",
            local_key="kanji_composition_id",
            remote_key="kanji_id",
        ),
    ]
