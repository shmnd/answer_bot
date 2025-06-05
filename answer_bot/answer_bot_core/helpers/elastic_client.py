# elastic_client.py ✅
from elasticsearch import Elasticsearch
from django.conf import settings

auth_config = {}
if settings.ELASTIC_USER and settings.ELASTIC_USER_PASS:
    auth_config['basic_auth'] = (settings.ELASTIC_USER, settings.ELASTIC_USER_PASS)

es = Elasticsearch(
    'http://host.docker.internal:9200',
    **auth_config,
    verify_certs=False,
    # ca_certs=settings.CA_CERTS_PATH,
)