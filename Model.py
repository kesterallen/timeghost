
import datetime
import random
import logging

from google.appengine.ext import ndb

class TimeGhostError(ValueError):
    pass

class EventError(TimeGhostError):
    pass

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m',
                '%Y']

class Event(ndb.Model):
    date = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()

    @classmethod
    def _parse_date_str(cls, date_str):
        date = None
        for fmt in DATE_FORMATS:
            try:
                date = datetime.datetime.strptime(date_str, fmt)
            except ValueError as err:
                pass

        if date is None:
            raise EventError("Couldn't parse date '%s'" % date_str)

        return date

    @classmethod
    def build(cls, date_str, description=None):
        date = Event._parse_date_str(date_str)
        if description is None:
            description = "date '%s'" % date_str
        event = Event(description=description, date=date)
        return event

    @classmethod
    def get_from_key_or_date(cls, kod, description=None):
        """
        If "key-or-date" input is a key, extract that event from the datastore.
        If it is a date, create a non-datastore Event from that date.
        """
        try:
            event = ndb.Key(urlsafe=kod).get()
        except:
            event = Event.build(date_str=kod, description=description)

        if event is None:
            raise EventError("Something wrong in get_from_key_or_date(%s)", kod)

        return event

    @classmethod
    def now(cls):
        event = Event(date=datetime.datetime.now(),
                      description="today")
        return event

    @classmethod
    def get_random(cls, before=None):
        """Inputs:
            before - an Event
        """
        earliest = Event.get_earliest()
        events = Event.query(
                     ).filter(Event.date < before.date
                     ).filter(Event.date > earliest.date
                     ).fetch()
        event = random.choice(events)
        logging.debug("get_random %s %s", events, event)
        return event

    @classmethod
    def get_latest(cls):
        event = Event.query().order(-Event.date).get()
        logging.debug("get_latest %s", event)
        return event

    @classmethod
    def get_earliest(cls):
        event = Event.query().order(Event.date).get()
        logging.debug("get_earliest%s", event)
        return event

    @classmethod
    def get_events_in_range(cls, now, middle_kod):
        """
        Get the Events that ar valid timeghost.long_ago events for
        middle=middle and now=now.
        """
        event = Event.get_from_key_or_date(middle_kod)
        timeghost = TimeGhost(now=now, middle=event)
        earliest_date = event.date - timeghost.now_td()

        events = Event.query(
                     ).filter(Event.date < event.date
                     ).filter(Event.date > earliest_date
                     ).order(-Event.date
                     ).fetch()
        return events

    @classmethod
    def get_earlier_than(cls, key_or_date=None):
        if key_or_date:
            event = Event.get_from_key_or_date(key_or_date)
            events = Event.query(
                         ).filter(Event.date < event.date
                         ).order(-Event.date
                         ).fetch()
        else:
            events = Event.query().order(-Event.date).fetch()

        return events

    def __sub__(self, other):
        """Return the timedelta between two Events' .date attributes."""
        return self.date - other.date

    def __cmp__(self, other):
        return cmp(self.date, other.date)

    def __repr__(self):
        return "{0.description} ({0.date})".format(self)

    @property
    def legendstr(self):
        return "{0.description} ({0.date.year})".format(self)

    @property
    def date_ymd(self):
        return self.date.isoformat().strip().split("T")[0]

class TimeGhost(object):

    TIME_RANGE = 0.5

    def _validate_event_ordering(self):
        order_test = []
        if self.now is not None:
            order_test.append(self.now)
        if self.middle is not None:
            order_test.append(self.middle)
        if self.long_ago is not None:
            order_test.append(self.long_ago)

        if len(order_test) > 1:
            for i in range(1, len(order_test)):
                newer = order_test[i-1]
                older = order_test[i]
                if older > newer:
                    raise TimeGhostError(
                            "bad event ordering for timeghost %s" % self)

    def __init__(self, now=None, middle=None, long_ago=None, display_prefix="The "):
        self.now = now
        self.middle = middle
        self.long_ago = long_ago

        self._validate_event_ordering()

        self.display_prefix = display_prefix


    def now_td(self, factor=None):
        """Get the timedelta between self.now and self.middle, optionally
        scaled by "factor"."""
        timedelta = self.now - self.middle
        if factor:
            upper_edge = timedelta.days * factor
            timedelta = datetime.timedelta(days=upper_edge)
        return timedelta

    @property
    def now_td_years(self):
        return self.now_td().days / 365.25

    def then_td(self):
        td = self.middle - self.long_ago
        return td

    @property
    def then_td_years(self):
        return self.then_td().days / 365.25

    def find_best_long_ago(self):
        """Return the best long_ago event based on self.middle and self.now."""

        wanted_date_earliest = self.middle.date - self.now_td()
        wanted_date_latest = self.middle.date - self.now_td(TimeGhost.TIME_RANGE)

        events = Event.query().filter(Event.date > wanted_date_earliest
                             ).filter(Event.date < self.middle.date
                             ).order(Event.date)
        try:
            logging.info("find_best_long_ago: looking for date > %s and < %s",
                      wanted_date_earliest, wanted_date_latest)
            good_range_events = events.filter(Event.date < wanted_date_latest)
            event = random.choice(good_range_events.fetch())
        except IndexError:
            try:
                logging.info("Didn't find anyting. Trying between %s and %s",
                          wanted_date_earliest, self.middle.date)
                event = random.choice(events.fetch())
            except IndexError as err:
                logging.info("Nothing there either. Getting earliest.")
                event = Event.get_earliest()
        except:
            raise TimeGhostError("can't find an event between %s and %s" %
                      (self.middle.date, wanted_date_earliest))

        logging.debug("find_best_long_ago: event = %s", event)
        return event

    def key_url(self, which='now'):
        """
        Return the timeghost.{which}.key.urlsafe(), if it exists. If the
        timeghost.event exists, but does not have a key (user-specified dates
        like '1980', for example), return the date. If the event doesn't exist,
        return None.

        Used in the templates.
        """

        try:
            event = getattr(self, which)
        except AttributeError as err:
            logging.debug("No event '%s' in timeghost.key_url, returning None",
                          which)
            return None

        try:
            key = event.key.urlsafe()
        except AttributeError as err:
            logging.debug("Event '%s' in doesn't have .key.urlsafe() in "
                          "timeghost.key_url, returning event.date",
                          which)
            return event.date.year

        return key

    @property
    def factoid(self):
        tmpl = "{0.display_prefix}{0.middle.description} "\
               "is closer to the {0.long_ago.description} "\
               "than {0.now.description}"
        try:
            output = tmpl.format(self)
        except AttributeError as err:
            print err
            output = "This timeghost is incomplete (%s)" % err
        return output

    def __repr__(self):
        return """TimeGhost--
    now: {0.now};
    middle: {0.middle};
    long_ago: {0.long_ago}""".format(self)

