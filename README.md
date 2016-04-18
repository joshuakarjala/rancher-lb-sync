# Requirements

- Docker (http://docker.io/)
- Rancher (http://rancher.com/)

# Environment

To allow the container to act as Rancher agent it needs the following labels (which automatically expose agent credentials to the service):
```yml
labels:
    io.rancher.container.create_agent: true
    io.rancher.container.agent.role: environment
    ...
```

The following environment variables should be set on the reload service:
```yml
environment:
    PROJECT_ID: 1d3 # The Rancher Project ID
    LOADBALANCER_ID: 1s333 # The internal Rancher ID of your load balancer
    WEBHOOK_URL: foo.bar.com/webhook # Updates to the loadbalancer will be posted to this webhook [optional]
    ...
```

# Registering your services

Your services can automatically register them selves with the loadbalancer by providing the following labels:
```yml
labels:
    rancher.lb.sync.register: true # This service wants to be registered)
    rancher.lb.sync.domain: bar.com # The domain we are registering the service on)
    rancher.lb.sync.ext_port: 80 # The external port on the loadbalancer we map to)
    rancher.lb.sync.service_port: 3000 # The port of our service our we mapping)
    rancher.lb.sync.name: foo # The name we want to register our service with (defaults to the service name)
    rancher.lb.sync.full_name: (*.)bar.com # Overwrites the combo of domain + name
    ...
```
These settings would map the service to `foo.bar.com`

# Webhook

If you set the `WEBHOOK_URL` environment variable then a webhook will be posted everytime the load balancer is updated. The payload looks like this:
```json
[{
    "serviceId": "2s38",
    "ports": ["service1.foo.bar.com:80=3000"]
}, {
    "serviceId": "1s432",
    "ports": ["service2.bar.cpp.com:80=8080"]
},
...
]
```

# Props

Based on the work over at https://github.com/mediadepot/docker-rancher-events
