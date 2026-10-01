from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne


@register_model
class WordModel(EntityModel):
    name = "word"
    table_name = "words"
    url_prefix = "/words"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        ManyToMany(
            attribute="sentences",
            target="sentence",
            association_table="sentence_word",
            local_key="word_id",
            remote_key="sentence_id",
        ),
    ]
