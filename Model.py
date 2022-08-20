
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

DAYS_IN_YEAR = 365.25

DATE_FORMATS = [
    '%Y-%m-%d %H:%M:%S', # 2020-01-26 11:56:23
    '%Y-%m-%d %H:%M',    # 2020-01-26 11:56
    '%Y-%m-%d',          # 2020-01-26
    '%Y-%m',             # 2020-01
    '%Y',                # 2020
    '%Y %m %d %H:%M:%S', # 2020 01 26 11:56:23
    '%Y %m %d',          # 2020 01 26
    '%Y %m',             # 2020 01
    '%B %d, %Y',         # January 26, 2020
    '%b %d %Y',          # Jan 26 2020
    '%B %d, %Y',         # January 26, 2020
    '%b %d %Y',          # Jan 26 2020
    '%d %B %Y',          # 26 January 2020
    '%d %b %Y',          # 26 Jan 2020
    '%d %B, %Y',         # 26 January, 2020
    '%d %b, %Y',         # 26 Jan, 2020
    '%Y %d %B',          # 2020 26 January
    '%Y %d %b',          # 2020 26 January

    '%m/%d/%Y',          # 01/26/2020
    '%m/%Y',             # 01/2020
    '%m/%d/%y',          # 01/26/20
    '%m/%y',             # 01/20
]

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
        for date_format in DATE_FORMATS:
            try:
                date = datetime.datetime.strptime(date_str, date_format)
                break
            except ValueError:
                pass

        if date is None:
            raise EventError("Couldn't parse date '{}'".format(date_str))

        return date

    @classmethod
    def build(
        cls, date_str, description=None, created_on=None, created_by=None, approved=False
    ):
        date = Event._parse_date_str(date_str)
        if description is None:
            description = "date '{}'".format(date_str)
        event = Event(
            description=description,
            date=date,
            created_on=created_on,
            created_by=created_by,
            approved=approved,
        )
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
        except Exception as err: # TODO: specific exception for key not found
            # Try matching 'kod' to short_url, construct a temp Event otherwise
            event = Event.query().filter(Event.short_url == kod).get()
            if event is None:
                event = Event.build(date_str=kod, description=description)

        if event is None:
            raise EventError("Something wrong in get_from_key_or_date ({})".format(kod))

        return event

    @classmethod
    def now(cls):
        now = datetime.datetime.now()
        event = Event(date=now, description="today")
        event.set_short_url()
        return event

    @classmethod
    def approved_query(cls):
        query = Event.query().filter(Event.approved == True)
        return query

    @classmethod
    def between_query(cls, earlier_than, later_than):
        query = (
            Event.approved_query()
            .filter(Event.date < earlier_than)
            .filter(Event.date > later_than)
        )
        return query

    @classmethod
    def get_random(cls, before=None):
        """Inputs: before - an Event """
        earliest = Event.get_earliest()
        events = Event.between_query(earlier_than=before.date, later_than=earliest.date).fetch()
        event = random.choice(events)
        return event

    @classmethod
    def get_latest(cls):
        event = Event.approved_query().order(-Event.date).get()
        return event

    @classmethod
    def get_earliest(cls):
        event = Event.approved_query().order(Event.date).get()
        return event

    @classmethod
    def get_events_in_range(cls, now, middle_kod, sort_asc=True):
        """
        Get the Events that are valid timeghost.long_ago events for
        middle=middle and now=now.
        """
        event = Event.get_from_key_or_date(middle_kod)
        timeghost = TimeGhost(now=now, middle=event)
        earliest_date = event.date - timeghost.now_td.td

        query = Event.between_query(earlier_than=event.date, later_than=earliest_date)
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
            events = (
                Event.approved_query()
                .filter(Event.date < event.date)
                .order(-Event.date)
                .fetch()
            )
        else:
            events = Event.approved_query().order(-Event.date).fetch()
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


class TimeGhostDelta(object):
    def __init__(self, beginning, ending):
        self.td = beginning.date - ending.date

    def verbose_between(self, other):
        """
        a) the time deltas are more than a year apart, print only the year
           values,
        b) the difference between the length of the time deltas is less than
           a year but more than a day, print "year int(days)",
        c) otherwise, the difference between the length of the time deltas is
            less than a day, print "year float(days)"
        """
        add_days = False
        add_fractional_days = False

        # E.g. "8 years" or "1 year"
        txt = "{} year".format(self.years_int)
        if self.years_int != 1:
            txt += "s"

        # Add number of days if the absolute value is less than 1 year, make it
        # a fractional number if it is less than 1 day:
        if self.years < 1:
            add_days = True
        if self.days < 1:
            add_fractional_days = True

        # 1) If the two time deltas have a different number of years, proceed.
        # 2) If the two time deltas have the same number of years, but a
        #    different number of days, print the int days:
        # 3) If the two time deltas have the same number of years AND days,
        #    print the float (:.1f) days:
        if self.years_int != other.years_int:
            pass
        elif self.days_int != other.days_int:
            add_days = True
        else:
            add_fractional_days = True

        if add_days:
            txt += ", {.days_int} day".format(self)
        elif add_fractional_days:
            txt += ", {.days_int:.1f} day".format(self)

        # Suffix: "days" or "day"
        if add_days or add_fractional_days:
            if self.days_int != 1:
                txt += "s"

        return txt

    @property
    def years(self):
        return float(self.td.days) / DAYS_IN_YEAR

    @property
    def years_int(self):
        return int(self.years)

    @property
    def days(self):
        return DAYS_IN_YEAR * (self.years - self.years_int)

    @property
    def days_int(self):
        return int(self.days)


class TimeGhost(object):

    TIME_RANGE = 0.5

    def _validate_event_ordering(self):
        order_test = [e for e in [self.now, self.middle, self.long_ago] if e]

        if len(order_test) == 0:
            return

        for i in range(1, len(order_test)):
            newer = order_test[i-1]
            older = order_test[i]
            if older > newer:
                raise TimeGhostError("bad event ordering for timeghost {}".format(self))

    def _make_tds(self):
        """time deltas for now->middle and middle->long ago"""
        if self.now and self.middle:
            self.now_td = TimeGhostDelta(self.now, self.middle)
        if self.middle and self.long_ago:
            self.then_td = TimeGhostDelta(self.middle, self.long_ago)


    def __init__(self, now=None, middle=None, long_ago=None, display_prefix="The "):
        self.now = now
        self.middle = middle
        self.long_ago = long_ago
        self.display_prefix = display_prefix

        self._validate_event_ordering()
        self._make_tds()

    def set(self, event, which_event):
        """ 
        Inputs: an Event object and a string of "now" "middle" or "long_ago"
        """
        if which_event == "now":
            self.now = event
        elif which_event == "middle":
            self.middle = event
        elif which_event == "long_ago":
            self.long_ago = event
        else:
            raise TimeGhostError(
                "The value {} isn't valid for TimeGhost.set".format(which_event))
        self._make_tds()

    def scaled_timedelta(self, factor):
        """Get the timedelta between self.now and self.middle, scaled by "factor"."""
        upper_edge = self.now_td.days * factor
        timedelta = datetime.timedelta(days=upper_edge)
        return timedelta

    def find_best_long_ago(self, get_earliest=False):
        """Return the best long_ago event based on self.middle and self.now."""

        wanted_date_earliest = self.middle.date - self.now_td.td
        wanted_date_latest = self.middle.date - self.scaled_timedelta(TimeGhost.TIME_RANGE)

        events = Event.between_query(earlier_than=self.middle.date, later_than=wanted_date_earliest).order(Event.date)
        try:
            good_range_events = events.filter(Event.date < wanted_date_latest).fetch()
            if get_earliest:
                event = good_range_events[0]
            else:
                event = random.choice(good_range_events)
        except IndexError:
            try:
                event = random.choice(events.fetch())
            except IndexError as err:
                event = Event.get_earliest()
        except:
            raise TimeGhostError(
                "can't find an event between {} and {}".format(
                    self.middle.date, wanted_date_earliest)
            )

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
    def true_since(self):
        """The date that this timeghost first was true."""
        return self.middle.date + self.then_td.td

    @property
    def factoid_list(self):
        return [
            s.encode("utf-8")
            for s in [
                self.display_prefix,
                self.middle.description,
                self.long_ago.description,
                self.now.description,
            ]
        ]

    @property
    def factoid(self):
        try:
            output = "{}{} is closer to the {} than {}".format(*self.factoid_list)
        except AttributeError as err:
            output = "This timeghost is incomplete ({})".format(err)
        return output

    @property
    def verbose(self):
        if self.middle.description == "Your birthday":
            middle = "Your birthday is "
            now = " before now"
        else:
            middle = self.display_prefix + self.middle.legendstr + " is "
            now = " before " + self.now.legendstr

        text_ = [
            middle,
            self.now_td.verbose_between(self.then_td),
            now,
            " but only ",
            self.then_td.verbose_between(self.now_td),
            " after the ",
            self.long_ago.legendstr,
            "."
        ]
        return "".join(text_)

    def __repr__(self):
        return """TimeGhost--
    now: {0.now};
    middle: {0.middle};
    long_ago: {0.long_ago}""".format(self)

