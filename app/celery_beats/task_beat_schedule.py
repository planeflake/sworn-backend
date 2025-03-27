from celery import Celery
from celery.schedules import crontab

app = Celery('task_services')

app.conf.beat_schedule = {
    'check-expired-tasks': {
        'task': 'check_expired_tasks',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'clean-completed-tasks': {
        'task': 'clean_completed_tasks',
        'schedule': crontab(hour=3, minute=0),  # Once per day at 3 AM
    },
}