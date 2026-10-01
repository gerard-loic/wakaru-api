from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne, OneToMany


@register_model
class ExerciseModel(EntityModel):
    name = "exercise"
    table_name = "exercise"
    url_prefix = "/exercise"
    relationships = [
        ManyToOne(attribute="category", target="category", foreign_key="category_id"),
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        OneToMany(attribute="exercise_items", target="exercise_item", foreign_key="exercise_id"),
    ]
