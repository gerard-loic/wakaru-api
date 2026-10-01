from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class Grammar_RuleModel(EntityModel):
    name = "grammar_rule"
    table_name = "grammar_rules"
    url_prefix = "/grammar_rules"
    relationships = [
        ManyToOne(attribute="category", target="category", foreign_key="category_id"),
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
    ]
