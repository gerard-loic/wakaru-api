from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class Sentence_TokenModel(EntityModel):
    name = "sentence_token"
    table_name = "sentence_tokens"
    url_prefix = "/sentence_tokens"
    relationships = [
        ManyToOne(attribute="sentence", target="sentence", foreign_key="sentence_id"),
        ManyToOne(attribute="sentence_token_role", target="sentence_token_role", foreign_key="sentence_token_role_id"),
        ManyToOne(attribute="word", target="word", foreign_key="word_id"),
    ]
