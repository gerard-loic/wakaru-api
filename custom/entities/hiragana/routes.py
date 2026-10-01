from custom.libs.knowledge_gating import build_knowledge_gated_router


def build_router(model, methods, *, create_validator, update_validator):
    return build_knowledge_gated_router(
        model,
        methods,
        create_validator=create_validator,
        update_validator=update_validator
    )
