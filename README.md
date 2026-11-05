Voir les logs

docker logs -f wakaru-api
# ou, via compose :
docker compose -f docker/docker-compose.yml logs -f sylo


#from custom.libs.knowledge_gating import build_knowledge_gated_router
from app.crud.routes import build_crud_router