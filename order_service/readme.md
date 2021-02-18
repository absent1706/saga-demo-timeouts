# Setup
```
pipenv install
pipenv run pip install 'asyncapi[http,yaml,redis,subscriber,docs]'
```

# Run
```
PYTHONPATH=. FLASK_DEBUG=1 FLASK_APP=order_service/app.py pipenv run flask run

```

or simply 
```
PYTHONPATH=. python order_service/app.py
```
