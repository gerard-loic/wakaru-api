from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class Composition_TypeModel(EntityModel):
    name = "composition_type"
    table_name = "composition_types"
    url_prefix = "/composition_types"
    relationships = [
        OneToMany(attribute="compositions", target="composition", foreign_key="composition_type_id"),
    ]
