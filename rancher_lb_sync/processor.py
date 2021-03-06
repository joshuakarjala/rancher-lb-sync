import logging
import json
import requests
import os

log = logging.getLogger('processor')

CATTLE_URL = os.getenv('CATTLE_URL')
CATTLE_ACCESS_KEY = os.getenv('CATTLE_ACCESS_KEY')
CATTLE_SECRET_KEY = os.getenv('CATTLE_SECRET_KEY')
PROJECT_ID = os.getenv('PROJECT_ID')
LOADBALANCER_ID = os.getenv('LOADBALANCER_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', False)


def make_get_request(url):
    return requests.get(url,
                        auth=(CATTLE_ACCESS_KEY, CATTLE_SECRET_KEY),
                        headers={
                            'Accept': 'application/json',
                            'Content-Type': 'application/json'
                        })


def make_post_request(url, json):
    return requests.post(url,
                         auth=(CATTLE_ACCESS_KEY, CATTLE_SECRET_KEY),
                         headers={
                             'Accept': 'application/json',
                             'Content-Type': 'application/json'
                         },
                         json=json)


def send_webhook(entries):
        log.info(' -- Sending Webhook!')
        r = requests.post(WEBHOOK_URL,
                          headers={
                              'Accept': 'application/json',
                              'Content-Type': 'application/json'
                          },
                          json=entries)
        r.raise_for_status()
        log.info(' -- Webhook sent!')


def process_message(event_message):
    def is_service_valid(service):
        return (service['state'] in ('active', 'removed') and
                service['type'] == 'service' and service['launchConfig']
                .get('labels', {}).get('rancher.lb.sync.register', False))

    def get_loadbalancer_service():
        r = make_get_request('%s/projects/%s/loadbalancerservices/%s' %
                             (CATTLE_URL, PROJECT_ID, LOADBALANCER_ID))
        r.raise_for_status()

        return r.json()

    def get_loadbalancer_entries():
        log.info(' -- Getting loadbalancer entries')
        r = make_get_request('%s/projects/%s/serviceconsumemaps?serviceId=%s' %
                             (CATTLE_URL, PROJECT_ID, LOADBALANCER_ID))

        r.raise_for_status()

        try:
            links = r.json()['data']
        except IndexError:
            raise Exception(' -- Load balancer consume map not found!')

        loadbalancer_entries = [{'ports': link['ports']} for link in links]

        log.info(' -- Current loadbalancer entries')
        log.info(loadbalancer_entries)

        return loadbalancer_entries

    def get_services():
        log.info(' -- Getting services')
        r = make_get_request('%s/projects/%s/services' %
                             (CATTLE_URL, PROJECT_ID))

        r.raise_for_status()

        try:
            services = r.json()['data']
        except IndexError:
            raise Exception(' -- No services found')

        services = filter(lambda s: is_service_valid(s), services)

        return services

    def add_loadbalancer_link(loadbalancer_service, loadbalancer_entry):
        log.info(' -- Adding loadbalancer link:')
        log.info(loadbalancer_entry)

        r = make_post_request(loadbalancer_service['actions']
                              ['addservicelink'],
                              {'serviceLink': loadbalancer_entry})
        r.raise_for_status()
        log.info(' -- Finished processing')

    def set_loadbalancer_links(loadbalancer_service, loadbalancer_entries):
        log.info(' -- Setting loadbalancer links:')
        log.info(loadbalancer_entries)

        r = make_post_request(loadbalancer_service['actions']
                              ['setservicelinks'],
                              {'serviceLinks': loadbalancer_entries})
        r.raise_for_status()
        log.info(' -- Finished processing')

    def remove_loadbalancer_link(loadbalancer_service, loadbalancer_entry):
        log.info(' -- Removing loadbalancer link:')
        log.info(loadbalancer_entry)

        r = make_post_request(loadbalancer_service['actions']
                              ['removeservicelink'],
                              {'serviceLink': loadbalancer_entry})
        r.raise_for_status()
        log.info(' -- Finished processing')

    def process_service(service):
        labels = service['launchConfig'].get('labels', {})
        domain = labels.get('rancher.lb.sync.domain', 'foo.com')
        service_name = labels.get('rancher.lb.sync.name', service['name'])
        ext_port = labels.get('rancher.lb.sync.ext_port', 80)
        service_port = labels.get('rancher.lb.sync.service_port', 3000)
        full_name = labels.get('rancher.lb.sync.full_name', False)

        if not full_name:
            full_name = '%s.%s' % (service_name, domain)

        ports = ['%s:%s=%s' % (name, ext_port, service_port) for name in full_name.split(',')]

        return {
            'serviceId': service['id'],
            'ports': ports
        }

    event = json.loads(event_message)

    # Ignore ping events
    if event['name'] == 'ping':
        return

    log.info('### Received Event Message: ' + event_message)

    # if event['resourceType'] == 'serviceConsumeMap':
    #     if event['data']['resource']['state'] == 'removed':
    #         if WEBHOOK_URL:
    #             send_webhook(get_loadbalancer_entries())

    # Only react to service events
    if event['resourceType'] != 'service':
        return

    log.info('### Received Event State: ' + event['data']['resource']['state'])

    if not event['data']['resource']['state'] in ['active', 'removed']:
        return

    loadbalancer_service = get_loadbalancer_service()
    services = get_services()

    loadbalancer_entries = [process_service(s) for s in services]

    set_loadbalancer_links(loadbalancer_service, loadbalancer_entries)
