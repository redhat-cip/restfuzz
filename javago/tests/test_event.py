#!/usr/bin/python

import unittest
import javago.event
from cStringIO import StringIO


class EventTests(unittest.TestCase):
    def test_event(self):
        e = javago.event.Event("test_event")

        class FakeResp:
            status_code = 42
            text = '{}'
        e.set_resp(FakeResp())
        self.assertTrue("test_event" in str(e))


class EventDbTests(unittest.TestCase):
    def test_event_list(self):
        tmp_file = StringIO()
        db = javago.event.EventDb(tmp_file)
        # insert 10 events
        for idx in xrange(10):
            event = javago.event.Event("test%03d" % idx)
            db.append(event)
        # check event list
        idx = 0
        for e in db.list():
            self.assertEquals(e.name, "test%03d" % idx)
            idx += 1
        self.assertEquals(idx, 10)
