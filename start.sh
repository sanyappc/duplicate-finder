pkill python
pkill filecheck.py
nohup celery -A tasks worker --loglevel=info &
nohup ./filecheck.py &
