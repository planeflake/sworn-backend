# app/workers/celery_app.py
from celery import Celery

# Create the Celery application
app = Celery('rpg_game',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0',
             include=[
                 'app.workers.settlement_worker',
                 'app.workers.trader_worker',
                 'app.workers.trader_worker_new',
                 'app.workers.animal_worker',
                 'app.workers.item_worker',
                 'app.workers.time_worker',
                 'app.workers.area_worker',
                 'app.workers.world_worker',
                 'app.workers.shared_worker_utils',
                 'app.workers.task_worker'
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
            'task': 'app.workers.settlement_worker.process_all_settlements',
            'schedule': 30.0,  # Every 30 seconds
        },
        'process-all-traders': {
            'task': 'app.workers.trader_worker.process_all_traders',
            'schedule': 20.0,  # Every 20 seconds
        },
        'process-all-traders-mcts': {
            'task': 'app.workers.trader_worker_new.process_all_traders',
            'schedule': 30.0,  # Every 30 seconds
        },
        'advance-game-day': {
            'task': 'app.workers.world_worker.advance_game_day',
            'schedule': 120.0,  # Every 2 minutes (simulates daily time progression)
        },
        'process-all-animals': {
            'task': 'app.workers.animal_worker.process_all_animals',
            'schedule': 60.0,  # Every minute
        },
        'animal-migrations': {
            'task': 'app.workers.animal_worker.migrate_animals',
            'schedule': 3600.0,  # Every hour
        },
        'process-all-areas': {
            'task': 'app.workers.area_worker.process_all_areas',
            'schedule': 90.0,  # Every 90 seconds
        },
        'process-all-items': {
            'task': 'app.workers.item_worker.process_all_items',
            'schedule': 300.0,  # Every 5 minutes
        },
        'process-expired-tasks': {
            'task': 'app.workers.task_worker.process_expired_tasks',
            'schedule': 900.0,  # Every 15 minutes
        },
        'clean-completed-tasks': {
            'task': 'app.workers.task_worker.clean_completed_tasks',
            'schedule': 86400.0,  # Once per day
        },
        'notify-task-deadlines': {
            'task': 'app.workers.task_worker.notify_task_deadlines',
            'schedule': 3600.0,  # Once per hour
        },
        'create-random-trader-tasks': {
            'task': 'app.workers.trader_worker_new.create_random_trader_tasks',
            'schedule': 1800.0,  # Every 30 minutes
            'kwargs': {'task_count': 2}  # Create 2 random tasks each time
        }
    }
)

if __name__ == '__main__':
    app.start()