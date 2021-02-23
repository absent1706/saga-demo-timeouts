Saga pattern for mircoservices example.
Has `order_service` which is the saga entrypoint and 3 other services with workers handling commands: `consumer_service`, `restaurant_service`, `accounting_service`.

It's basically an implementation of CreateOrderSaga from [Chris Richardson book on Microservices](https://microservices.io/book)

# Run
Firstly, run all infrastructure 
```
docker-compose up --build --remove-orphans
```
Then, try out visiting http://localhost:5001 in your browser or just

```
curl localhost:5000
```

# Local development
Firstly, run RabbitMQ and Redis
```
docker-compose  --file docker-compose.local.yaml up 
```

To run each service, see `readme.md` files in each service folder. 