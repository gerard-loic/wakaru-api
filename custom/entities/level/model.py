from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class LevelModel(EntityModel):
    name = "level"
    table_name = "levels"
    url_prefix = "/levels"
    relationships = [
        OneToMany(attribute="exercise", target="exercise", foreign_key="level_id"),
        OneToMany(attribute="grammar_rules", target="grammar_rule", foreign_key="level_id"),
        OneToMany(attribute="kanjis", target="kanji", foreign_key="level_id"),
        OneToMany(attribute="sentences", target="sentence", foreign_key="level_id"),
        OneToMany(attribute="users", target="user", foreign_key="level_id"),
        OneToMany(attribute="words", target="word", foreign_key="level_id"),
    ]
