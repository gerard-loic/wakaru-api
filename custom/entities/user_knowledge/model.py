from app.crud.model import EntityModel, register_model
from app.crud.relationships import ManyToOne


@register_model
class User_KnowledgeModel(EntityModel):
    name = "user_knowledge"
    table_name = "user_knowledges"
    url_prefix = "/user_knowledges"
    relationships = [
        ManyToOne(attribute="user", target="user", foreign_key="user_id"),
    ]
