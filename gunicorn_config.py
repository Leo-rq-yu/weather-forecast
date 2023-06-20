import multiprocessing

# The address and port to bind to
bind="0.0.0.0:8080"

# The number of worker processes for handling requests
workers = multiprocessing.cpu_count() * 2 + 1

# The type of worker process to use
worker_class = "gthread"

# The maximum number of requests a worker will process before restarting
max_requests = 500

# The maximum number of simultaneous clients a worker will accept
backlog = 2048

# The timeout for graceful worker restarts
timeout = 30

# The path to your Flask application instance
app = "app:app"

# Logging configuration
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr