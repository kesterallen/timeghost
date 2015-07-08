"""Main program for timeghost."""

from flask import Flask, render_template, request, redirect
from google.appengine.ext import ndb
import logging

from Controller import EventSeeder, TimeGhostFactory, EVENTS_FILE
from Model import Event, TimeGhost, TimeGhostError


app = Flask(__name__)
app.config['DEBUG'] = True

# Seed new events
@app.route('/seed')
def seed_events_from_file(filename=EVENTS_FILE):
    try:
        events = EventSeeder.seed(filename=filename)
        return render_template('events.html', events=events, title="New Seeded Events")
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# All events
@app.route('/events')
def events_server():
    """
    Show a page of all the events.
    """
    try:
        events = Event.query().order(-Event.date).fetch()
        return render_template('events.html', events=events, title="All Events")
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# Specific Event
@app.route('/specific', methods=['POST', 'GET'])
@app.route('/s', methods=['POST', 'GET'])
def chosen_event_server():
    """
    Generate a timeghost for a user-selected event. The if block generates the
    result, and the else block generates the request page.
    """
    try:
        # Render requested timeghost
        if request.method == "POST":
            middle_key = request.form['middle']
            middle = Event.get_from_key_or_date(middle_key)
            now = Event.now()

            timeghost = TimeGhostFactory.build_from_events(now, middle)
            return render_template('timeghost.html', timeghost=timeghost)
        # wraw the form:
        else:
            events = Event.query().order(-Event.date).fetch()
            return render_template('specific.html', events=events)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# Permalinks
@app.route('/permalink/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>/<long_ago_key_urlsafe>')
def permalink_server(middle_key_urlsafe, long_ago_key_urlsafe=None):
    """
    Handles permalinks for a particular timeghost if both arguments
    are given, and TimeGhosts between now and a particular middle event if
    only the middle event key is given.
    """
    try:
        now = Event.now()
        middle = Event.get_from_key_or_date(middle_key_urlsafe)
        long_ago = None

        if long_ago_key_urlsafe is not None:
            long_ago = Event.get_from_key_or_date(long_ago_key_urlsafe)

        timeghost = TimeGhostFactory.build_from_events(now, middle, long_ago)

        return render_template('timeghost.html', timeghost=timeghost)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

@app.route('/')
@app.route('/<middle_date_str>')
@app.route('/<middle_date_str>/<now_date_str>')
def timeghost_server(middle_date_str=None, now_date_str=None):
    """
    Generates a random timeghost, a timeghost between now and a particular
    time, or a timeghost between two specified times, depending on the number
    of arguments given.
    """
    try:
        if now_date_str is None:
            now = Event.now()
        else:
            now = Event.build(date_str=now_date_str)

        if middle_date_str is None:
            middle = Event.get_random(before=now)
        else:
            middle = Event.build(date_str=middle_date_str)

        timeghost = TimeGhostFactory.build_from_events(now=now, middle=middle)
        logging.debug("output timeghost: %s", timeghost)

        return render_template('timeghost.html', timeghost=timeghost)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# Birthday
@app.route('/birthday', methods=['POST', 'GET'])
@app.route('/b', methods=['POST', 'GET'])
def birthday_server():
    """
    Generate a timeghost for a user-selected birth year. The if block
    generates the result, and the else block generates the request page.
    """
    if request.method == "POST":
        try:
            now = Event.now()
            birthday_str = request.form['bday']
            middle = Event.build(date_str=birthday_str, description="Your birthday")

            timeghost = TimeGhostFactory.build_from_events(now=now, middle=middle)
            timeghost.display_prefix = ""
            logging.debug("birthday output timeghost: %s", timeghost)

            return render_template('timeghost.html', timeghost=timeghost)
        except TimeGhostError as err:
            return render_template('error.html', err=err), 404
    else:
        return render_template('birthday.html')

@app.errorhandler(404)
def page_not_found(err):
    return render_template('error.html', err=err, info="Page Not Found"), 404
