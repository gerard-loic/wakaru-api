from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class Theme_WordModel(EntityModel):
    name = "theme_word"
    table_name = "theme_words"
    url_prefix = "/theme_words"
    relationships = [
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        ManyToOne(attribute="word", target="word", foreign_key="word_id"),
    ]
