from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne


@register_model
class CompositionModel(EntityModel):
    name = "composition"
    table_name = "compositions"
    url_prefix = "/compositions"
    relationships = [
        ManyToOne(attribute="composition_type", target="composition_type", foreign_key="composition_type_id"),
        ManyToOne(attribute="word", target="word", foreign_key="word_id"),
        ManyToMany(
            attribute="kanjis",
            target="kanji",
            association_table="composition_kanji",
            local_key="composition_id",
            remote_key="kanji_id",
        ),
    ]
