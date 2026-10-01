from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToMany, ManyToOne


@register_model
class SentenceModel(EntityModel):
    name = "sentence"
    table_name = "sentences"
    url_prefix = "/sentences"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        ManyToMany(
            attribute="kanjis",
            target="kanji",
            association_table="sentence_kanji",
            local_key="sentence_id",
            remote_key="kanji_id",
        ),
        ManyToMany(
            attribute="words",
            target="word",
            association_table="sentence_word",
            local_key="sentence_id",
            remote_key="word_id",
        ),
    ]
