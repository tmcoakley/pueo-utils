from threading import Timer

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class HskTimer(RepeatTimer):
    def __init__(self,
                 eventFifo,
                 eventType,
                 interval=1):
        self.eventFifo = eventFifo
        self.eventType = eventType
        self.tickCount = 0
        def tickFn():
            if not self.eventFifo.full():
                self.eventFifo.put([self.eventType,self.tickCount])
            self.tickCount = self.tickCount + 1
        super(HskTimer, self).__init__(interval, tickFn)
        
    
