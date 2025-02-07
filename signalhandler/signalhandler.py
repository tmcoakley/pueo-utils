# simple signal handler using the
# self-pipe trick to handle catching
# signals with multiple I/O watches
import selectors
import signal
import os

class SignalHandler:
    """ Quick & dirty signal handler using self-pipe trick & selectors """    
    def __init__(self, sel, signals = [ signal.SIGTERM, signal.SIGINT, signal.SIGPIPE ] ):
        """
        sel : selector used for multiple I/O handling
        signals : list of sigs to set terminate on (default TERM/INT)
        """
        noop = lambda s, f : None
        self.terminate = False
        self.rfd, self.wfd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        for sig in signals:
            signal.signal(sig, noop)
        signal.set_wakeup_fd(self.wfd)
        sel.register(self.rfd, selectors.EVENT_READ, self.set_terminate)

    def set_terminate(self, fd=None, mask=None):
        """ Set the terminate indicator. Called on reception of signal. """
        self.terminate = True
        
    
