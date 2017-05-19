'''
    Wrap logging module.
    Load logging configuration, and setting output path.
'''
import os
import logging
import logging.config
import settings

def init(path='/var/log', port=8080):
    '''
        Load logging configuration and modify output directory based on the
        given port.
        Initialize operating execute only ones for each web application. 
    '''
    global init
    # create log folder with listening port
    log_file = os.path.join(path, '{}.log'.format(port))
    handler_config = settings['log']['handlers']
    handler_config['file']['filename'] = log_file
    # handler_config['rotate_file']['filename'] = '/'.join([path, 'radius.log'])

    # read logging initial config and initial logger
    logging.config.dictConfig(settings['log'])
    # assign an anonymous function(the function only return None) to init
    init = lambda x=None, y=None: None  

def logger(logger_name='log', propagate=False):
    '''
        Get special logger
        logger_name : logger name 
    '''
    init()
    logger = logging.getLogger(logger_name)
    logger.propagate = propagate
    return logger

