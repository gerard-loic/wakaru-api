from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class Exercise_CategoryModel(EntityModel):
    name = "exercise_category"
    table_name = "exercise_categories"
    url_prefix = "/exercise_categories"
    relationships = [
        OneToMany(attribute="exercises", target="exercise", foreign_key="exercise_category_id"),
    ]
