from elasticsearch import Elasticsearch
from django.conf import settings

PASSWORD = settings.ELASTIC_USER_PASS
ES_CA_CERT_PATH = settings.CA_CERTS_PATH

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", PASSWORD),
    verify_certs=True, # "False" Use only for local development; for prod, set up certs properly
    ca_certs=ES_CA_CERT_PATH,
)
