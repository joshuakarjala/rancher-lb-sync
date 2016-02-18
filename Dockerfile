FROM python:2.7.11
MAINTAINER joshua@fluxuries.com

COPY ./rancher_lb_sync /rancher-lb-sync/rancher_lb_sync

COPY ./requirements.txt /rancher-lb-sync/requirements.txt
COPY ./start.sh /rancher-lb-sync/start.sh

RUN chmod u+x  /rancher-lb-sync/start.sh

WORKDIR /rancher-lb-sync
RUN pip install -r requirements.txt

CMD ["/rancher-lb-sync/start.sh"]
