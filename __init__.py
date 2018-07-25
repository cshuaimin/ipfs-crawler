import coloredlogs

coloredlogs.DEFAULT_LOG_FORMAT = '%(asctime)s %(name)s %(levelname)s %(message)s'
coloredlogs.install(level='INFO')
