from elasticsearch import Elasticsearch
from django.conf import settings

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=(settings.ELASTIC_USER, settings.ELASTIC_USER_PASS),
    verify_certs=True,
    ca_certs=settings.CA_CERTS_PATH,
)