# workers/celery_app.py
from celery import Celery

# Create the Celery application
app = Celery('rpg_game',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0',
             include=[
                 'workers.settlement_worker',
                 'workers.trader_worker',
                 'workers.time_worker',
                 'workers.shared_worker_utils'
             ])

# Optional configurations
app.conf.update(
    result_expires=3600,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Define your beat schedule if needed
    beat_schedule={
        'process-all-settlements': {
            'task': 'workers.shared_worker_utils.process_all_settlements',
            'schedule': 30.0,  # Every 5 minutes
        },
        'process-all-traders': {
            'task': 'workers.trader_worker.process_all_traders',
            'schedule': 20.0,  # Every 10 minutes
        },
        'advance-game-day': {
            'task': 'workers.time_worker.advance_game_day',
            'schedule': 120.0,  # Daily (24 hours)
        }
    }
)

if __name__ == '__main__':
    app.start()