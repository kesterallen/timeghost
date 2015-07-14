
import csv
import logging
import os

from Model import Event, TimeGhost, TimeGhostError

EVENTS_FILE = 'events.csv'

class EventSeeder(object):
    @classmethod
    def seed(cls, filename=None):
        """Add Events which don't already exist in the database."""
        if filename is None:
            dirname = os.path.dirname(__file__)
            filename = os.path.join(dirname, EVENTS_FILE)

        events = []
        with open(filename) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                date = row[0]
                desc = row[1]
                event = Event.build(date_str=date, description=desc)
                exists = Event.query(Event.description ==
                                     event.description).get()
                if not exists:
                    event.put()
                    events.append(event)

        return events

class TimeGhostFactory(object):
    @classmethod
    def build(cls, now=None, middle=None, long_ago=None):
        timeghost_in = TimeGhost(now=now, middle=middle, long_ago=long_ago)
        timeghost = TimeGhostFactory.build_from_timeghost(timeghost_in)
        return timeghost

    @classmethod
    def build_from_timeghost(cls, timeghost):
        """Return a completed TimeGhost based on the partial TimeGhost
        request."""

        logging.debug("TimeGhostFactory.build: %s" % timeghost)

        # Timeghost between now and a random event
        if timeghost.middle is None:
            timeghost.middle = Event.get_random()
        # Timeghost for now and given middle, no long_ago
        elif timeghost.now is not None and \
             timeghost.middle is not None and \
             timeghost.long_ago is None:
            pass
        # Fully specified timeghost. Just return it.
        elif timeghost.now is not None and \
             timeghost.middle is not None and \
             timeghost.long_ago is not None:
            return timeghost
        # Otherwise error
        else:
            raise TimeGhostError("bad case in TimeGhostFactory.build for %s",
                                 timeghost)

        logging.debug("TimeGhostFactory.build: %s" % timeghost)
        try:
            best_long_ago = timeghost.find_best_long_ago()
        except TimeGhostError:
            best_long_ago = Event.get_earliest()
        logging.debug("TimeGhostFactory.build: %s" % best_long_ago)

        output_timeghost = TimeGhost(now=timeghost.now,
                                     middle=timeghost.middle,
                                     long_ago=best_long_ago)
        logging.debug("TimeGhostFactory.build: %s" % output_timeghost)
        return output_timeghost

