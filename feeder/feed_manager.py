from feeder.motor import feed
from config import *

auto_feed_enabled = AUTO_FEED_DEFAULT

def manual_feed():

    feed()

def enable_auto_feed():

    global auto_feed_enabled

    auto_feed_enabled = True

def disable_auto_feed():

    global auto_feed_enabled

    auto_feed_enabled = False

def is_auto_feed_enabled():

    return auto_feed_enabled