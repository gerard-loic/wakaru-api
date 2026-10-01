from app.crud.model import EntityModel, register_model


@register_model
class KatakanaModel(EntityModel):
    name = "katakana"
    table_name = "katakanas"
    url_prefix = "/katakanas"
    relationships = [
    ]
