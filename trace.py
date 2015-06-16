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
    # log_path = os.path.join(path, 'bidong')
    # check logs folder
    if not os.path.exists(path):
        os.mkdir(path)
    # create log folder with listening port
    bidong_path = os.path.join(path, 'p_{}'.format(port))
    if not os.path.exists(bidong_path):
        os.mkdir(bidong_path)
    handler_config = settings['log']['handlers']
    handler_config['file']['filename'] = '/'.join([bidong_path, 'service.log'])
    handler_config['error']['filename'] = '/'.join([bidong_path, 'error.log'])
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

