#!/usr/bin/python -S

"""Utility for attempting to join a list of BSSIDs."""

import time

try:
  import monotime  # pylint: disable=unused-import,g-import-not-at-top
except ImportError:
  pass
try:
  _gettime = time.monotonic
except AttributeError:
  _gettime = time.time


class AgingPriorityCycler(object):
  """A modified priority queue.

  1)  Items are not removed from the queue, but automatically reinserted (thus
      "cycler" rather than "queue").
  2)  Baseline priority is multiplied by time in queue.

  This data structure is not efficient and may not scale well.  Don't use it for
  anything big.

  As a minor optimization, items must be hashable.  This restriction could be
  removed, but we don't have a use case for non-hashable values yet.
  """

  def __init__(self, cycle_length_s=0, items=()):
    """Initializes the queue.

    Args:
      cycle_length_s: The minimum amount of time an item will spend in the
      queue after being automatically reinserted.
      items: Initial items for the queue, as tuples of (item, priority).
    """
    self._min_time_in_queue_s = cycle_length_s
    self._items = {}
    if items:
      self.update(items)

  def empty(self):
    return not self._items

  def insert(self, item, priority):
    """Insert a new item, or update the priority of an existing item."""
    try:
      self._items[item][0] = priority
    except KeyError:
      self._items[item] = [priority, _gettime()]

  def remove(self, item):
    if item in self._items:
      self._items.pop(item)

  def peek(self):
    """Return the next item in the queue, but do not cycle it."""
    return self._find_next(cycle=False)

  def next(self):
    """Return the next item in the queue.

    Also resets that item's age to now + cycle_length_s.

    Returns:
      The next item in the queue.
    """
    return self._find_next(True)

  def _find_next(self, cycle=False):
    """Implementation of peek and next."""
    if self.empty():
      return

    now = _gettime()

    def aged_priority(key_value):
      _, (priority, birth) = key_value
      return priority * (now - birth)

    result, value = max(self._items.iteritems(), key=aged_priority)
    if value[1] > now:
      return

    if cycle:
      value[1] = now + self._min_time_in_queue_s

    return result

  def update(self, items):
    """Update to the given items, adding new ones and removing old ones.

    Args:
      items:  An iterable of (item, priority).
    """
    now = _gettime()
    new_items = {}
    for item, priority in items:
      t = now
      existing = self._items.get(item, None)
      if existing:
        t = existing[1]
      new_items[item] = [priority, t]

    self._items = new_items

  def __len__(self):
    return len(self._items)

