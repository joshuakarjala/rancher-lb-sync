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
    LOADBALANCER_STACK_NAME: bar # The name of the stack which has your loadbalancer
    LOADBALANCER_SERVICE_NAME: lb # The of the loadbalancer service
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
    ...
```
These settings would map the service to `foo.bar.com`

# Props

Based on the work over at https://github.com/mediadepot/docker-rancher-events
