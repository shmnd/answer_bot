from elasticsearch import Elasticsearch
from django.conf import settings

es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=(settings.ELASTIC_USER, settings.ELASTIC_USER_PASS),
    verify_certs=False,
    ca_certs=settings.CA_CERTS_PATH,
)