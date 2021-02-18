# Setup
```
pipenv install
pipenv run pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
```

# Run worker
```
PYTHONPATH=. pipenv run celery -A restaurant_service.worker worker --loglevel=INFO
```

# Run API docs server 
```
PYTHONPATH=. asyncapi-docs --api-module restaurant_service.asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```