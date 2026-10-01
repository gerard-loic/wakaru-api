from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class Exercise_ItemModel(EntityModel):
    name = "exercise_item"
    table_name = "exercise_items"
    url_prefix = "/exercise_items"
    relationships = [
        ManyToOne(attribute="exercise", target="exercise", foreign_key="exercise_id"),
    ]
