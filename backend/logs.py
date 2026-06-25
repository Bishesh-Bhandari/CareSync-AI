import logging
import os


def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'app.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('HealthSync')