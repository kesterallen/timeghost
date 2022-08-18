
import csv
import os

from Model import Event, TimeGhost, TimeGhostError

EVENTS_FILE = "events.csv"


class EventSeeder(object):
    """
    Parse filename to create new Events. Existing Events are not duplicated.
    """

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
                exists = Event.query(Event.description == event.description).get()
                if not exists:
                    event.put()
                    events.append(event)

        return events


class TimeGhostFactory(object):
    """
    Create TimeGhost objects from triplets of events, or generate a complete
    TimeGhost based on a partial TimeGhost.
    """

    @classmethod
    def build(cls, now=None, middle=None, long_ago=None, get_earliest=False):
        """
        Create TimeGhost objects from triplets of events.
        """
        timeghost_in = TimeGhost(now=now, middle=middle, long_ago=long_ago)
        timeghost = TimeGhostFactory.build_from_timeghost(timeghost_in, get_earliest)
        return timeghost

    @classmethod
    def build_from_timeghost(cls, timeghost, get_earliest=False):
        """
        Return a completed TimeGhost based on the partial TimeGhost request.
        """
        # Set the now Event if not specified:
        if timeghost.now is None:
            timeghost.now = Event.now()

        # Generate a middle Event if not specified:
        if timeghost.middle is None:
            timeghost.middle = Event.get_random()

        # Generate a long_ago Event if not specified:
        if timeghost.long_ago is None:
            try:
                timeghost.long_ago = timeghost.find_best_long_ago(get_earliest)
            except TimeGhostError:
                timeghost.long_ago = Event.get_earliest()

        # Return a new instance to insure the init validation is run properlhy:
        return TimeGhost(timeghost.now, timeghost.middle, timeghost.long_ago)

