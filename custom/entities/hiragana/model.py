from app.crud.model import EntityModel, register_model


@register_model
class HiraganaModel(EntityModel):
    name = "hiragana"
    table_name = "hiraganas"
    url_prefix = "/hiraganas"
    relationships = [
    ]
