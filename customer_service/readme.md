# Run worker
```
pipenv run celery -A worker worker --loglevel=INFO
```

# Run API docs server 
```
PYTHONPATH=. asyncapi-docs --api-module asyncapi_specification

curl http://127.0.0.1:5000/asyncapi.yaml
```