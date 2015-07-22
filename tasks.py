from celery import Celery
from hashlib import md5

def get_md5(client, path):
    with client.get_file(path) as file:
        return md5(file.read()).digest()

def get_pathes(client, path, extensions):
    d = dict()
    for x in client.metadata(path)['contents']:
        if x['is_dir']:
            d.update(get_pathes(client, x['path'], extensions))
        elif x['path'].endswith(extensions):
            d[x['path']] = x['bytes']
    return d

app = Celery('tasks', broker='mongodb://localhost:27017/', backend='mongodb://localhost:27017/')
app.conf.update(CELERY_TASK_RESULT_EXPIRES=18000)

@app.task
def check_task(client, path, extensions=[]):
    pathes = get_pathes(client, path, tuple(extensions))
    group_size = dict()
    for key, value in sorted(pathes.items()):
        group_size.setdefault(value, []).append(key)
    group_md5 = dict()
    for element in group_size.values():
        if len(element) > 1:
            for value in element:
                group_md5.setdefault(get_md5(client, value), []).append(value)
    return [g for g in group_md5.values() if len(g) > 1]
