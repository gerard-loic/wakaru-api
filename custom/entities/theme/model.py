from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, OneToMany


@register_model
class ThemeModel(EntityModel):
    name = "theme"
    table_name = "themes"
    url_prefix = "/themes"
    relationships = [
        OneToMany(attribute="exercises", target="exercise", foreign_key="theme_id"),
        OneToMany(attribute="grammar_rules", target="grammar_rule", foreign_key="theme_id"),
        OneToMany(attribute="sentences", target="sentence", foreign_key="theme_id"),
        OneToMany(attribute="theme_words", target="theme_word", foreign_key="theme_id"),
        ManyToMany(
            attribute="kanjis",
            target="kanji",
            association_table="theme_kanji",
            local_key="theme_id",
            remote_key="kanji_id",
        ),
    ]
