
import csv
import logging
import os
import unittest

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
    def build_from_events(cls, now, middle, long_ago=None):
        timeghost_in = TimeGhost(now=now, middle=middle, long_ago=long_ago)
        timeghost = TimeGhostFactory.build(timeghost_in)
        return timeghost

    @classmethod
    def build(cls, timeghost):
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

class TestTimeGhost(unittest.TestCase):
    def setUp(self):
        self.events = EventSeeder.seed()

    def test_now(self):
        timeghost = TimeGhost(now=self.events[0])

    def test_middle(self):
        timeghost = TimeGhost(middle=self.events[10])

    def test_now_middle(self):
        timeghost = TimeGhost(now=self.events[0], middle=self.events[1])

    def test_now_middle_bad(self):
        with self.assertRaises(TimeGhostError):
            timeghost = TimeGhost(now=self.events[1], middle=self.events[0])

    def test_delta(self):
        timeghost = TimeGhost(now=self.events[0],
                              middle=self.events[1],
                              long_ago=self.events[2])
        self.assertTrue(timeghost.now_td())
        self.assertTrue(timeghost.then_td())

    def test_factory_case1(self):
        partial_tg = TimeGhost(now=self.events[0])
        tg = TimeGhostFactory.build(partial_tg)
        print tg.factoid


def main():
    events = EventSeeder.seed()

    for i in range(5):
        partial_tg = TimeGhost(now=events[0])
        tg = TimeGhostFactory.build(partial_tg)
        print tg.factoid

    #mt_st_helens = events[17]
    #partial_tg = TimeGhost(now=events[0], middle=mt_st_helens)
    #tg = TimeGhostFactory.build(partial_tg)
    #print tg.factoid

if __name__ == '__main__':
    unittest.main()
    #main()
