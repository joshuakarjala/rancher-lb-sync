import logging
import json
import requests
import os
from notify import Notify

log = logging.getLogger("listener")


class Processor:
    ignored_resource_types = ['mount', 'ipAddress', 'nic', 'volume', 'port']

    def __init__(self, rancher_event):
        self._raw = rancher_event
        self.event = json.loads(rancher_event)

        self.api_endpoint = os.getenv('CATTLE_URL')
        self.access_key = os.getenv('CATTLE_ACCESS_KEY')
        self.secret_key = os.getenv('CATTLE_SECRET_KEY')
        self.loadbalancer_stack = os.getenv('LOADBALANCER_STACK_NAME')
        self.loadbalancer_service = os.getenv('LOADBALANCER_SERVICE_NAME')

    def make_get_request(self, url):
        return requests.get(url,
                            auth=(self.access_key, self.secret_key),
                            headers={
                                'Accept': 'application/json',
                                'Content-Type': 'application/json'
                            })

    def make_post_request(self, url, json):
        return requests.post(url,
                             auth=(self.access_key, self.secret_key),
                             headers={
                                 'Accept': 'application/json',
                                 'Content-Type': 'application/json'
                             },
                             json=json)

    def get_loadbalancer_service(self):
        r = self.make_get_request('%s/environments?name=%s' %
                                  (self.api_endpoint. self.loadbalancer_stack))
        r.raise_for_status()
        try:
            loadbalancer_stack = r.json()["data"].pop()
        except IndexError:
            raise Exception('Load balancer stack not found!')

        r = self.make_get_request("%s?name=%s" %
                                  (loadbalancer_stack["links"]["services"],
                                   self.loadbalancer_service))
        r.raise_for_status()

        try:
            return r.json()["data"].pop()
        except IndexError:
            raise Exception('Load balancer service not found!')

    def get_stacks(self):
        log.info(' -- Retrieving all Stacks')
        # list of running stacks, called environments in api
        r = self.make_get_request(self.api_endpoint + '/environments')
        r.raise_for_status()
        return r.json()["data"]

    def get_registered_stack_services(self, stack):
        log.info(' -- -- Retrieving services in stack: ' + stack['name'])
        # get the current active services
        r = self.make_get_request(stack['links']['services'])
        r.raise_for_status()
        services = r.json()["data"]

        # Filter so we only have services with rancher.lb.sync.register = True
        return filter(lambda service: service['type'] is 'service' and
                      service['launchConfig'].get('labels', {})
                      .get('rancher.lb.sync.register', False), services)

    def get_registered_services(self, stacks):
        registered_services = [self.get_registered_stack_services(stack)
                               for stack in stacks]

        # have to flatten the list
        return [service for sublist in registered_services
                for service in sublist]

    def process_service(self, service):
        labels = service['launchConfig'].get('labels', {})
        domain = labels.get('rancher.lb.sync.domain', 'foo.com')
        ext_port = labels.get('rancher.lb.sync.ext_port', 80)
        service_port = labels.get('rancher.lb.sync.service_port', 3000)
        service_name = labels.get('rancher.lb.sync.name', service['name'])

        return {
            'serviceId': service['id'],
            'ports': [
                '%s.%s:%d:%d' % (service_name, domain, ext_port, service_port)
            ]
        }

    def make_loadbalancer_entries(self, services):
        return [self.process_service(service) for service in services]

    def start(self):
        # Ignore pings
        if self.event['name'] is 'ping':
            return

        # Only react to service events
        if self.event['resourceType'] is not 'service':
            return

        if self.event['data']['resource']['state'] in ('active', 'removed'):
            log.info('Detected a change in Rancher services ' +
                     '- Begin processing.')

            # get the current event's stack information
            r = self.make_get_request(self.event['data']['resource']
                                      ['links']['environment'])
            r.raise_for_status()
            # service_stack_response = r.json()

            # notify = Notify(service_stack_response,
            #                 'started' if self.event['data']['resource']['state'] == 'active' else 'stopped')
            # notify.send()

            stacks = self.get_stacks()
            registered_services = self.get_registered_services(stacks)

            loadbalancer_entries = \
                self.make_loadbalancer_entries(registered_services)

            loadbalancer_service = \
                self.get_loadbalancer_service()

            self.set_loadbalancer_links(loadbalancer_service,
                                        loadbalancer_entries)

    def set_loadbalancer_links(self, loadbalancer_service,
                               loadbalancer_entries):
        log.info(' -- Setting loadbalancer entries:')
        log.info(loadbalancer_entries)

        r = self.make_post_request(loadbalancer_service['actions']
                                   ['setservicelinks'],
                                   {"serviceLinks": loadbalancer_entries})
        r.raise_for_status()
        log.info('Finished processing')
