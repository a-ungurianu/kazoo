"""Child and Data watching higher level API's

"""
import logging
import threading

from kazoo.client import KazooState

log = logging.getLogger(__name__)


class ChildrenWatch(object):
    def __init__(self, client, path, func, allow_session_lost=True):
        """Create a children watcher for a path

        :param client: A zookeeper client
        :type client: :class:`~kazoo.client.KazooClient`
        :param path: The path to watch for children on
        :type path: str
        :param func: Function to call initially and every time the
                     children change. `func` will be called with a
                     single argument, the list of children.
        :type func: callable
        :param allow_session_lost: Whether the watch should be
                                   re-registered if the zookeeper
                                   session is lost.
        :type allow_session_lost: bool

        The path must already exist for the children watcher to
        run.

        """
        self._client = client
        self._path = path
        self._func = func
        self._stopped = False
        self._watch_established = False
        self._run_lock = threading.Lock()

        # Register our session listener if we're going to resume
        # across session losses
        if allow_session_lost:
            self._client.add_listener(self._session_watcher)
        self._get_children()

    def _get_children(self):
        with self._run_lock:  # Ensure this runs one at a time
            if self._stopped:
                return

            children = self._client.retry(self._client.get_children,
                                          self._path, self._watcher)
            if not self._watch_established:
                self._watch_established = True

            try:
                if self._func(children) is False:
                    self._stopped = True
            except Exception as exc:
                log.exception(exc)
                raise

    def _watcher(self, event):
        self._get_children()

    def _session_watcher(self, state):
        if state == KazooState.LOST:
            self._watch_established = False
        elif state == KazooState.CONNECTED and \
             not self._watch_established and not self._stopped:
            self._get_children()
