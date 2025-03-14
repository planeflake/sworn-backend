# Celery configuration options
# These settings will be imported by celery_app.py

# Broker settings
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
broker_connection_retry_on_startup = True

# Serialization
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# Timezone
timezone = 'UTC'
enable_utc = True

# Task execution
task_acks_late = True  # Tasks are acknowledged after execution
worker_prefetch_multiplier = 1  # Don't prefetch more than one task
result_expires = 86400  # Results expire after 1 day
worker_max_tasks_per_child = 200  # Worker process is replaced after handling 200 tasks

# Import paths need to include the 'workers.' prefix
imports = [
    'workers.trader_tasks',
    'workers.settlement_tasks',
]