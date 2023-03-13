"""Main program for timeghost."""

from flask import Flask, render_template, request, make_response
from google.appengine.api import mail, search, users
import logging
import datetime
import json
import StringIO
import csv

from Controller import EventSeeder, TimeGhostFactory, EVENTS_FILE
from Model import Event, TimeGhost, TimeGhostError

EVENT_SEARCH_INDEX = 'event_search_index'

app = Flask(__name__)
app.config['DEBUG'] = True

# TODO: finish
@app.route('/search')
def event_search():
    print("HI")
    print("HI")
    print("HI")
    print("HI")
    print("HI")
    print("HI")
    search_term = request.get('search_term')
    import pdb; pdb.set_trace()
    search_term = '"%s"' % search_term.replace('"', '')
    search_term = search_term.encode('unicode-escape')

    event_search_index = search.Index(EVENT_SEARCH_INDEX)
    results = event_search_index.search(search_term)
    logging.debug('search results are "{}"'.format(results))
    events = [ndb.Key(urlsafe=r.doc_id).get() for r in results]
    events = [e for e in events if e is not None]

    return("HI")

@app.route('/addallsearchdocs')
def add_all_search_docs():
    event_search_index = search.Index(EVENT_SEARCH_INDEX)
    events = Event.query().fetch()
    count = 0
    for event in events:
        count += 1
        doc = event.search_doc
        event_search_index.put(doc)
        #event.put() # TODO Uncomment to go live
    title = "Updated {} events to add search doc".format(count)
    return render_template('events.html', events=events, title=title)

@app.route('/raves')
def show_testimonials():
    return render_template('raves.html')

@app.route('/addshorturl')
def addshorturl():
    #user = users.get_current_user()
    #now = datetime.datetime.now()

    #events = Event.query().filter(Event.created_by == None).fetch()
    #events = Event.query().filter(Event.short_url == None).fetch()
    events = Event.query().fetch()
    count = 0
    for event in events:
        count += 1
        #event.created_on = now
        #event.created_by = user
        #event.approved = True
        event.set_short_url()
        #event.put() # TODO Uncomment to go live
    title = "Updated %s events to add a short_url" % count
    return render_template('events.html', events=events, title=title)

# Approve all # TODO remove this
@app.route('/approve_all', methods=['POST', 'GET'])
def approve_all():
    events = Event.query().fetch()
    for event in events:
        event.approved = True
        event.put()
    return "HI"

# Add a single new event:
@app.route('/add', methods=['POST', 'GET'])
def add_event_server():
    """ Add a new event, or draw the form to do so """
    try:
        user = users.get_current_user()
        now = datetime.datetime.now()

        # POST: parse the form input
        if request.method == "POST":
            date_str = request.form['date_str']
            description = request.form['description']
            created_on = datetime.datetime.now()
            created_by = user
            approved = users.is_current_user_admin()

            event = Event.build(
                date_str=date_str,
                description=description,
                created_on=now,
                created_by=created_by,
                approved=approved)
            event.set_short_url()
            event.put()

            mail.send_mail(
                sender="Kester Allen <kester@gmail.com>",
                to="Kester Allen <kester+timeghost@gmail.com>",
                subject="Event added",
                body="Event %s was added" % event)

            rt = render_template('events.html', events=[event], title="Added one event")

        # GET: draw the form:
        else:
            if user:
                text = "Logout, %s" % user.nickname()
                url = users.create_logout_url('/')
            else:
                text = "Login"
                url = users.create_login_url('/')

            rt = render_template('add.html', login_url=url, login_text=text)
    except TimeGhostError as err:
        rt = render_template('error.html', err=err), 404
    return rt

# Seed new events from EVENTS_FILE
@app.route('/seed')
def seed_events_from_file(filename=EVENTS_FILE):
    try:
        events = EventSeeder.seed(filename=filename)
        return render_template('events.html',
                               events=events,
                               title="New Seeded Events")
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

@app.route('/events_json', methods=['POST', 'GET'])
@app.route('/events_json/<middle_key_or_date>', methods=['POST', 'GET'])
@app.route('/j', methods=['POST', 'GET'])
@app.route('/j/<middle_key_or_date>', methods=['POST', 'GET'])
def events_json_server(middle_key_or_date=None):
    """
    Either all events, or all events in the 'timeghost range' between than a
    given middle event key/date and now.
    """
    if request.method == "POST":
        middle_key_or_date = request.form['middle_event_key']
    events = Event.get_events_in_range(Event.now(),
                                       middle_key_or_date,
                                       sort_asc=False)
    events_in_dicts = [{'key': e.key.urlsafe(),
                        'description': e.description,
                        'date': "({0.year}-{0.month}-{0.day})".format(e.date),
                            } for e in events]

    json_events = json.dumps({'events': events_in_dicts})
    return json_events

@app.route('/events')
@app.route('/events/<middle_key_or_date>')
def events_server(middle_key_or_date=None):
    """
    Show a page of all the events, or all events EARLIER than a given key/date
    """
    try:
        events = Event.get_earlier_than(middle_key_or_date)
        title = "Earlier Events" if middle_key_or_date else "All Events"
        return render_template('events.html', events=events, title=title)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# All events, as a CSV
@app.route('/file')
def events_file_server():
    si = StringIO.StringIO()
    cw = csv.writer(si)
    events = Event.get_earlier_than()
    cw.writerows([(e.date, e.description) for e in events])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=events.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def form_for_now_middle(fieldname, form, description, do_events=False, select_vars=None, get_earliest=False):
    """
    Render a form, or the response to the form. Pulls out the specified field
    and uses that to generate a TimeGhost.middle. TimeGhost.now is Event.now().
    """
    try:
        # POST: Render the response to a form (a requested timeghost):
        if request.method == "POST":
            middle_key_or_date = request.form[fieldname]
            middle = Event.get_from_key_or_date(middle_key_or_date, description)
            timeghost = TimeGhostFactory.build(middle=middle, get_earliest=get_earliest)
            if not do_events:
                timeghost.display_prefix = ""

            return render_template('timeghost.html', timeghost=timeghost)
        # GET: Draw the form; its HTML filename is in the "form" variable:
        else:
            events = None
            if do_events:
                events = Event.query().order(-Event.date).fetch()
            if select_vars is not None:
                return render_template(form, events=events, **select_vars)
            else:
                return render_template(form, events=events)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# A chosen timeghost:
#
@app.route('/specific_both', methods=['POST', 'GET'])
@app.route('/sb', methods=['POST', 'GET'])
def chosen_event_pair():
    try:
        # Render requested timeghost
        if request.method == "POST":
            now = Event.now()

            middle_kod = request.form['middle']
            middle = Event.get_from_key_or_date(middle_kod)

            long_ago_kod = request.form['long_ago']
            long_ago = Event.get_from_key_or_date(long_ago_kod)

            timeghost = TimeGhost(now=now, middle=middle, long_ago=long_ago)
            return render_template('timeghost.html', timeghost=timeghost)
        # draw the form:
        else:
            events = Event.query().order(-Event.date).fetch()
            return render_template('specific_both.html', events=events)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

# Specific Event
@app.route('/specific', methods=['POST', 'GET'])
@app.route('/s', methods=['POST', 'GET'])
def chosen_event_server():
    """ Generate a timeghost for a user-selected event."""
    fieldname = 'middle'
    form = 'specific_one.html'
    description = None
    select_vars = dict(form_action="/s", form_legend="Pick an Event to Timeghost!", form_default_option_text="Timeghost an event!")
    return form_for_now_middle(fieldname, form, description, do_events=True, select_vars=select_vars)

# Specific Event, timeghost with oldest long_ago, middle specified with URL
@app.route('/sw/<short_url>')
def earliest_event_by_short_url_server(short_url):
    try:
        middle = Event.get_from_key_or_date(short_url)
    except TimeGhostError as err:
        raise TimeGhostError("timeghost doesn't know your birthday")
    timeghost = TimeGhostFactory.build(middle=middle, get_earliest=True)
    return render_template('timeghost.html', timeghost=timeghost)

# Specific Event, timeghost with oldest long_ago
@app.route('/specific_worst', methods=['POST', 'GET'])
@app.route('/sw', methods=['POST', 'GET'])
def earliest_chosen_event_server():
    """ Generate a worst-case timeghost for a user-selected event."""
    fieldname = 'middle'
    form = 'specific_one.html'
    select_vars = dict(form_action="/sw", form_legend="Pick an Event to Worst-Timeghost!", form_default_option_text="Worst-Timeghost an event!")
    return form_for_now_middle(fieldname, form, description=None, do_events=True, select_vars=select_vars, get_earliest=True)

# Fight Club, I am Jack's old movie reference
@app.route('/jack', methods=['POST', 'GET'])
@app.route('/fight_club', methods=['POST', 'GET'])
@app.route('/fc', methods=['POST', 'GET'])
def fight_club_server():
    """ Generate a timeghost for the release of Fight Club """
    fight_club = Event.get_from_key_or_date(
        'ag9zfnRpbWVnaG9zdC1hcHByEgsSBUV2ZW50GICAgICG7IcKDA')
    timeghost = TimeGhostFactory.build(middle=fight_club)
    return render_template('fight_club.html', timeghost=timeghost)

# Birthday
@app.route('/birthday', methods=['POST', 'GET'])
@app.route('/birthday/<birthday_date>', methods=['POST', 'GET'])
@app.route('/b', methods=['POST', 'GET'])
@app.route('/b/<birthday_date>', methods=['POST', 'GET'])
def birthday_server(birthday_date=None):
    """ Generate a timeghost for a user-selected birth year."""
    fieldname = 'bday'
    form = 'birthday.html'
    description = "Your birthday"

    if birthday_date:
        middle = Event.get_from_key_or_date(birthday_date)
        timeghost = TimeGhostFactory.build(middle=middle)
        return render_template('timeghost.html', timeghost=timeghost)
    else:
        return form_for_now_middle(fieldname, form, description)

# Permalinks
@app.route('/p/<middle_key_urlsafe>')
@app.route('/p/<middle_key_urlsafe>/<long_ago_key_urlsafe>')
def permalink_server(middle_key_urlsafe, long_ago_key_urlsafe=None):
    """
    Handles permalinks for a particular timeghost if both arguments
    are given, and TimeGhosts between now and a particular middle event if
    only the middle event key is given.
    """
    try:
        if middle_key_urlsafe == 'your-birthday':
            raise TimeGhostError("timeghost doesn't know your birthday")

        middle = Event.get_from_key_or_date(middle_key_urlsafe)
        long_ago = None

        if long_ago_key_urlsafe is not None:
            long_ago = Event.get_from_key_or_date(long_ago_key_urlsafe)


        timeghost = TimeGhostFactory.build(middle=middle, long_ago=long_ago)
        return render_template('timeghost.html', timeghost=timeghost)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404

@app.route('/tweet')
def timeghost_json():
    """Generate a random Timeghost and return it as a JSON object"""
    middle = Event.get_random(before=Event.now())
    timeghost = TimeGhostFactory.build(middle=middle)
    tries_left= 5
    max_good_ratio = 7 # random guess
    is_bad = True
    while tries_left > 0 and is_bad:
        tries_left -= 1
        timeghost = TimeGhostFactory.build(middle=middle)
        is_bad = timeghost.ratio > max_good_ratio
    return timeghost.tweet_json

# Main page: generate a Timeghost and display it
@app.route('/')
@app.route('/<middle_date_str>')
@app.route('/<middle_date_str>/<now_date_str>')
@app.route('/')
@app.route('/<middle_date_str>')
@app.route('/<middle_date_str>/<now_date_str>')
def fast_timeghost_server(middle_date_str=None, now_date_str=None):
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

        timeghost = TimeGhostFactory.build(middle=middle)

        return render_template('timeghost.html', timeghost=timeghost)
    except TimeGhostError as err:
        return render_template('error.html', err=err), 404


@app.errorhandler(404)
def page_not_found(err):
    return render_template('error.html', err=err, info="Page Not Found"), 404
