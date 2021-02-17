# Setup
```
pipenv install
pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
```

# Run worker
```
PYTHONPATH=. pipenv run celery -A accounting_service.worker worker --loglevel=INFO
```

# Run API docs server 
```
PYTHONPATH=. asyncapi-docs --api-module accounting_service.asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```