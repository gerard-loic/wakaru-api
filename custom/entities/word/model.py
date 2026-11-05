from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne, OneToMany


@register_model
class WordModel(EntityModel):
    name = "word"
    table_name = "words"
    url_prefix = "/words"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="partofspeech", target="partofspeeche", foreign_key="partofspeech_id"),
        OneToMany(attribute="compositions", target="composition", foreign_key="word_id"),
        OneToMany(attribute="sentence_tokens", target="sentence_token", foreign_key="word_id"),
        OneToMany(attribute="theme_words", target="theme_word", foreign_key="word_id"),
    ]
