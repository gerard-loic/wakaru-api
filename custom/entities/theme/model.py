from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class ThemeModel(EntityModel):
    name = "theme"
    table_name = "themes"
    url_prefix = "/themes"
    relationships = [
        OneToMany(attribute="exercise", target="exercise", foreign_key="theme_id"),
        OneToMany(attribute="grammar_rules", target="grammar_rule", foreign_key="theme_id"),
        OneToMany(attribute="kanjis", target="kanji", foreign_key="theme_id"),
        OneToMany(attribute="sentences", target="sentence", foreign_key="theme_id"),
        OneToMany(attribute="words", target="word", foreign_key="theme_id"),
    ]
