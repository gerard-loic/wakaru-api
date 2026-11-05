from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class PartofspeecheModel(EntityModel):
    name = "partofspeeche"
    table_name = "partofspeeches"
    url_prefix = "/partofspeeches"
    relationships = [
        OneToMany(attribute="words", target="word", foreign_key="partofspeech_id"),
    ]
