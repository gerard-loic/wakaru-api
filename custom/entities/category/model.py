from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class CategoryModel(EntityModel):
    name = "category"
    table_name = "categories"
    url_prefix = "/categories"
    relationships = [
        OneToMany(attribute="exercise", target="exercise", foreign_key="category_id"),
        OneToMany(attribute="grammar_rules", target="grammar_rule", foreign_key="category_id"),
    ]
