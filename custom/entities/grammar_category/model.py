from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class Grammar_CategoryModel(EntityModel):
    name = "grammar_category"
    table_name = "grammar_categories"
    url_prefix = "/grammar_categories"
    relationships = [
        OneToMany(attribute="grammar_rules", target="grammar_rule", foreign_key="grammar_category_id"),
    ]
