## Timeghost

A web app to generate factoids about the relative differnce between three events.
It makes you feel old. Live at [Timeghost](http://timeghost-app.appspot.com).

## API Reference


@app.route('/seed')

@app.route('/events')

@app.route('/specific', methods=['POST', 'GET'])
@app.route('/s', methods=['POST', 'GET'])

@app.route('/permalink/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>/<long_ago_key_urlsafe>')

@app.route('/')
@app.route('/<middle_date_str>')
@app.route('/<middle_date_str>/<now_date_str>')

@app.route('/birthday', methods=['POST', 'GET'])
@app.route('/b', methods=['POST', 'GET'])

## Author
[Kester Allen](http://twitter.com/@kesterallen)
