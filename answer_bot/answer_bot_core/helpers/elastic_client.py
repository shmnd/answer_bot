from elasticsearch import Elasticsearch
from django.conf import settings

password = settings.ELASTIC_USER_PASS

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", password),
    verify_certs=True, # "False" Use only for local development; for prod, set up certs properly
)
