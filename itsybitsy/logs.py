import logging

# logger
logger = logging.getLogger('itsybitsy')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s.%(filename)s.%(funcName)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
