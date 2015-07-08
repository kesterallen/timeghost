## Timeghost

A web app to generate factoids about the relative differnce between three events.
It makes you feel old. Live at [Timeghost](http://timeghost-app.appspot.com).

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

## Author
[Kester Allen](http://twitter.com/@kesterallen)
