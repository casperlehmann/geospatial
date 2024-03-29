import geocoder
import logging
import os
import json
from redis import Redis

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

def consumer(redis, queues = None):
    if queues is None:
        queues = ['queue']
    while True:
        consume(redis, queues, geocoder.osm)

def consume(redis, queues, open_street_map):
    popped = redis.blpop(queues)
    if popped is None:
        return
    payload = json.loads(popped[1])
    address = payload.get('address')
    latlng = payload.get('latlng')

    logging.info(f'Popped {address or latlng} off of the queue')
    if address:
        g = open_street_map(address)
        logging.info(f'Publishing {[g.lat, g.lng]}')
        redis.publish('response:'+address, json.dumps({'response': [g.lat, g.lng]}))
    elif latlng:
        r = open_street_map(latlng, method='reverse')
        logging.info(f'Publishing {[r.address]}')
        redis.publish(
            'response:'+latlng,
            json.dumps({'response': r.address}))

if __name__ == '__main__':
    redis = Redis(host='redis', decode_responses=True)
    consumer(redis)
