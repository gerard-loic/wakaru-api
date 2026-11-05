from app.crud.model import EntityModel, register_model
from app.crud.relationships import OneToMany


@register_model
class Sentence_Token_RoleModel(EntityModel):
    name = "sentence_token_role"
    table_name = "sentence_token_roles"
    url_prefix = "/sentence_token_roles"
    relationships = [
        OneToMany(attribute="sentence_tokens", target="sentence_token", foreign_key="sentence_token_role_id"),
    ]
