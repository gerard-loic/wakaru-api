from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class Kanji_CompositionModel(EntityModel):
    name = "kanji_composition"
    table_name = "kanji_compositions"
    url_prefix = "/kanji_compositions"
    relationships = [
        ManyToOne(attribute="kanji_record", target="kanji", foreign_key="kanji_id"),
        ManyToOne(attribute="kanjiword", target="kanjiword", foreign_key="kanjiword_id"),
    ]
