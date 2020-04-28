
import datetime
import random
import logging
from string import ascii_letters, digits

from google.appengine.api import search
from google.appengine.ext import ndb

class TimeGhostError(ValueError):
    """ Error class for TimeGhost actions.  """
    pass

class EventError(TimeGhostError):
    """ A specific Event error class.  """
    pass

DATE_FORMATS = ['%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m',
                '%Y']

class Event(ndb.Model):
    """ The Event model.  """
    date = ndb.DateTimeProperty(auto_now_add=True)
    description = ndb.StringProperty()
    short_url = ndb.StringProperty()
    created_on = ndb.DateTimeProperty(auto_now_add=True)
    created_by = ndb.UserProperty()
    approved = ndb.BooleanProperty()

    @classmethod
    def _parse_date_str(cls, date_str):
        date = None
        for fmt in DATE_FORMATS:
            try:
                date = datetime.datetime.strptime(date_str, fmt)
            except ValueError:
                pass

        if date is None:
            raise EventError("Couldn't parse date '{}'".format(date_str))

        return date

    @classmethod
    def build(cls, date_str,
                   description=None,
                   created_on=None,
                   created_by=None,
                   approved=False):
        date = Event._parse_date_str(date_str)
        if description is None:
            description = "date '{}'".format(date_str)
        event = Event(description=description,
                      date=date,
                      created_on=created_on,
                      created_by=created_by,
                      approved=approved)
        event.set_short_url()
        return event

    @classmethod
    def get_from_key_or_date(cls, kod, description=None):
        """
        If "key-or-date" input is a NDB key, extract that event from the
        datastore, If "key-or-date" is a short_url, extract that event, If it
        is a date, create a non-datastore Event from that date.
        """
        try:
            event = ndb.Key(urlsafe=kod).get()
        except: # TODO: specific exception for key not found
            # Try matching 'kod' to short_url, construct a temp Event otherwise
            event = Event.query().filter(Event.short_url == kod).get()
            if event is None:
                event = Event.build(date_str=kod, description=description)

        if event is None:
            raise EventError(
                "Something wrong in get_from_key_or_date ({})".format(kod))

        return event

    @classmethod
    def now(cls):
        now = datetime.datetime.now()
        event = Event(date=now, description="today")
        event.set_short_url()
        return event

    @classmethod
    def get_random(cls, before=None):
        """Inputs: before - an Event """
        earliest = Event.get_earliest()
        events = Event.query(
                     ).filter(Event.date < before.date
                     ).filter(Event.date > earliest.date
                     ).filter(Event.approved == True
                     ).fetch()
        event = random.choice(events)
        return event

    @classmethod
    def get_latest(cls):
        event = Event.query().filter(Event.approved == True).order(-Event.date).get()
        return event

    @classmethod
    def get_earliest(cls):
        event = Event.query().filter(Event.approved == True).order(Event.date).get()
        return event

    @classmethod
    def get_events_in_range(cls, now, middle_kod, sort_asc=True):
        """
        Get the Events that are valid timeghost.long_ago events for
        middle=middle and now=now.
        """
        event = Event.get_from_key_or_date(middle_kod)
        timeghost = TimeGhost(now=now, middle=event)
        earliest_date = event.date - timeghost.now_td()

        query = Event.query(
                     ).filter(Event.date < event.date
                     ).filter(Event.date > earliest_date
                     ).filter(Event.approved == True)
        if sort_asc:
            query = query.order(-Event.date)
        else:
            query = query.order(Event.date)

        events = query.fetch()
        return events

    @classmethod
    def get_earlier_than(cls, key_or_date=None):
        if key_or_date:
            event = Event.get_from_key_or_date(key_or_date)
            events = Event.query(
                         ).filter(Event.date < event.date
                         ).filter(Event.approved == True
                         ).order(-Event.date
                         ).fetch()
        else:
            events = Event.query(
                         ).filter(Event.approved == True
                         ).order(-Event.date
                         ).fetch()
        return events

    def __sub__(self, other):
        """Return the timedelta between two Events' .date attributes."""
        return self.date - other.date

    def __cmp__(self, other):
        return cmp(self.date, other.date)

    def __repr__(self):
        return "{} ({}) {} ({}) {}".format(
                self.description.encode('utf-8'),
                self.date,
                self.created_by,
                self.created_on,
                self.approved)

    def set_short_url(self):
        desc = self.description.lower().replace(' ', '-')
        alnums = (ascii_letters + digits + '-')
        short_url = "".join([c for c in desc if c in alnums])
        self.short_url = short_url[:40]

    @property
    def search_doc(self):
        doc = search.Document(
            doc_id = self.key.urlsafe(),
            fields=[
                search.TextField(name='description', value=self.description),
                # TODO: search.DateField??
            ],
        )
        return doc

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
    def int_now_td_years(self):
        return int(self.now_td_years)

    @property
    def now_td_years(self):
        return self.now_td().days / 365.25

    def then_td(self):
        timedelta = self.middle - self.long_ago
        return timedelta

    @property
    def int_then_td_years(self):
        return int(self.then_td_years)

    @property
    def then_td_years(self):
        return self.then_td().days / 365.25

    def find_best_long_ago(self, get_earliest=False):
        """Return the best long_ago event based on self.middle and self.now."""

        wanted_date_earliest = self.middle.date - self.now_td()
        wanted_date_latest = self.middle.date - self.now_td(TimeGhost.TIME_RANGE)

        events = Event.query().filter(Event.date > wanted_date_earliest
                             ).filter(Event.date < self.middle.date
                             ).filter(Event.approved == True
                             ).order(Event.date)
        try:
            good_range_events = events.filter(Event.date < wanted_date_latest)
            if get_earliest:
                event = good_range_events.fetch()[0]
            else:
                event = random.choice(good_range_events.fetch())
        except IndexError:
            try:
                event = random.choice(events.fetch())
            except IndexError as err:
                event = Event.get_earliest()
        except:
            raise TimeGhostError("can't find an event between %s and %s" %
                      (self.middle.date, wanted_date_earliest))

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
            logging.debug("No event '%s' in key_url, %s", which, err)
            return None

        try:
            #key = event.key.urlsafe()
            #return key
            return event.short_url
        except AttributeError as err:
            logging.debug("Event '%s' in doesn't have .key.urlsafe() in "
                          "timeghost.key_url, returning event.date",
                          which)
            return event.date.year

    @property
    def permalink(self):
        return "/p/{}/{}".format(self.key_url('middle'), self.key_url('long_ago'))

    @property
    def permalink_fully_qualified(self):
        return "https://timeg.host{}".format(self.permalink)

    @property
    def factoid(self):
        try:
            output = "%s%s is closer to the %s than %s" % (
                self.display_prefix.encode('utf-8'),
                self.middle.description.encode('utf-8'),
                self.long_ago.description.encode('utf-8'),
                self.now.description.encode('utf-8'),
            )  
        except AttributeError as err:
            print err
            output = "This timeghost is incomplete (%s)" % err
        return output

    @property
    def verbose(self):
      return "The {} is {} years before the {} but only {} years after the {}".format(
          self.middle.legendstr,
          self.int_now_td_years,
          self.now.legendstr,
          self.int_then_td_years,
          self.long_ago.legendstr
      )

    def __repr__(self):
        return """TimeGhost--
    now: {0.now};
    middle: {0.middle};
    long_ago: {0.long_ago}""".format(self)

