from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class Exercise_TypeModel(EntityModel):
    name = "exercise_type"
    table_name = "exercise_types"
    url_prefix = "/exercise_types"
    relationships = [
        OneToMany(attribute="exercises", target="exercise", foreign_key="exercise_type_id"),
    ]
