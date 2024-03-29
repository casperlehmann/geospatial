import json
import logging
import os
from redis import Redis
from quart import Quart, request, render_template, redirect

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

app = Quart(__name__)
app.redis = Redis(host='redis', decode_responses = True)

@app.route('/geo_code', methods=['POST'])
async def geo_code():
    """Endpoint for translating address to coordinates or reverse.

    Pass either an address to get back pair of latitute and longitute
    or pass pair of latitute and longitute to get back an address. Using
    open street map data.
    Arguments are passed as url parameters or as part of the POST request.
    Coordinates can be passed individually as lat and lng respectively
    or as a json-encoded list, i.e. latlng=[51.1576661,1.4458572].
    Priorities for arguments are: address, latlng, lat & lng.
    """
    form = await request.form
    address = request.args.get('address') or form.get('address')
    latlng = request.args.get('latlng') or form.get('latlng')
    lat, lng = request.args.get('lat') or form.get('lat'), request.args.get('lng') or form.get('lng')
    pubsub = app.redis.pubsub()
    if address:
        app.redis.rpush('queue', json.dumps({'address': address}))
        logging.info(f'Pushed {address} onto queue')
        pubsub.subscribe('response:'+address)
        label = 'latlng'
    elif latlng:
        app.redis.rpush('queue', json.dumps({'latlng': latlng}))
        logging.info(f'Pushed {latlng} onto queue')
        pubsub.subscribe('response:'+latlng)
        label = 'address'
    elif lat or lng:
        if not (lat and lng):
            return {'Error': 'Both lat and lng must be set'}, 400
        latlng = json.dumps([lat, lng])
        app.redis.rpush('queue', json.dumps({'latlng': latlng}))
        logging.info(f'Pushed {latlng} onto queue')
        pubsub.subscribe('response:'+latlng)
        label = 'address'
    else:
        return {'Error': 'No valid request received. Pass parameters as form- or URL-parameters.'}, 400
    for item in filter(lambda payload: payload.get('type') == 'message', pubsub.listen()):
        data = json.loads(item['data'])['response']
        logging.info(f'Returning {data} to client')
        return {label: data}

@app.route('/', methods=['GET'])
def get_index_page():
    """Redirect to the orders page"""
    return redirect('/index')

@app.route('/index', methods=['GET'])
async def page():
    return await render_template('/index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
