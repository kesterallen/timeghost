## Timeghost

A web app to generate factoids about the relative differnce between three events.
It makes you feel old. Live at [Timeghost](http://timeg.host).

## API Reference


Add all new events from the events.csv file. Admin only.
@app.route('/seed')

List all events in the db.
@app.route('/events')

Get a specific event.
@app.route('/specific', methods=['POST', 'GET'])
@app.route('/s', methods=['POST', 'GET'])

Serve a permalink.
@app.route('/permalink/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>/<long_ago_key_urlsafe>')

Generate a timeghost.
@app.route('/')
@app.route('/<middle_date_str>')
@app.route('/<middle_date_str>/<now_date_str>')

Generate a birthday timeghost.
@app.route('/birthday', methods=['POST', 'GET'])
@app.route('/b', methods=['POST', 'GET'])

## Domain Registration

The URL timeg.host is managed through https://ap.www.namecheap.com/domains/list/ 
Currently the redirect domain for timeg.host is pointed at https://timeghost-app.appspot.com/ via https://ap.www.namecheap.com/domains/domaincontrolpanel/timeg.host
If that doesn't work try using the https://cloud.google.com/appengine/docs/standard/python/mapping-custom-domains page

gcloud config set project timeghost-app && gcloud app deploy

## Author
[Kester Allen](http://twitter.com/@kesterallen)
