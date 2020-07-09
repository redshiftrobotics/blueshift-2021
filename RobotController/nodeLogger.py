'''
At one point, this file was used as a custom logger. It should be brought back with the logging system
'''
import logging
from pythonjsonlogger import jsonlogger
from queue import Queue


log_queue = Queue(0)

class nodeHandler(logging.Handler):
	def emit(self, record):
		global log_queue

		logEntry = self.format(record)
		print(type(logEntry))
		log_queue.put(logEntry)

logger = logging.getLogger(__name__)

jsonLogHandler = nodeHandler()
jsonFormatter = jsonlogger.JsonFormatter("%(asctime)s %(threadName)s %(levelname)s %(message)s")
jsonLogHandler.setFormatter(jsonFormatter)
logger.addHandler(jsonLogHandler)

logHandler = logging.StreamHandler()
logFormatter = logging.Formatter("%(asctime)s - %(threadName)s - %(levelname)s - %(message)s")
logHandler.setFormatter(logFormatter)
logger.addHandler(logHandler)
logger.setLevel(logging.DEBUG)

logger.debug("this doesn't work")

print(log_queue.get())
log_queue.task_done()