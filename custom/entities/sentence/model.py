from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne, OneToMany


@register_model
class SentenceModel(EntityModel):
    name = "sentence"
    table_name = "sentences"
    url_prefix = "/sentences"
    relationships = [
        ManyToOne(attribute="level", target="level", foreign_key="level_id"),
        ManyToOne(attribute="theme", target="theme", foreign_key="theme_id"),
        OneToMany(attribute="sentence_tokens", target="sentence_token", foreign_key="sentence_id"),
    ]
