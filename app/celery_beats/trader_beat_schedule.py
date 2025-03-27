from celery import Celery
from celery.schedules import crontab

app = Celery('trader_tasks')

app.conf.beat_schedule = {
    'process-trader-movement': {
        'task': 'process_trader_movement',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'args': ('trader_id',)  # Replace with dynamic trader IDs
    },
    'process-trader-encounters': {
        'task': 'process_trader_encounters',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'args': ('trader_id',)
    },
    'process-trader-wares': {
        'task': 'process_trader_wares',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
        'args': ('trader_id',)
    },
    'process-trader-health-and-logistics': {
        'task': 'process_trader_health_and_logistics',
        'schedule': crontab(hour='*/12'),  # Every 12 hours
        'args': ('trader_id',)
    },
    'process-trader-relationships': {
        'task': 'process_trader_relationships',
        'schedule': crontab(hour=0, minute=0),  # Once per day at midnight
        'args': ('trader_id',)
    },
    'process-trader-life-goal': {
        'task': 'process_trader_life_goal',
        'schedule': crontab(hour=1, minute=0),  # Once per day at 1 AM
        'args': ('trader_id',)
    },
    'process-all-traders': {
        'task': 'process_all_traders',
        'schedule': crontab(hour=2, minute=0),  # Once per day at 2 AM
    },
}