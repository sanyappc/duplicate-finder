#!/usr/bin/python3
from dropbox.client import DropboxOAuth2Flow as DBAuth, DropboxClient as DBClient
from bottle import route, template, post, run, request, redirect, response
from tasks import check_task

tpl = '''
<!DOCTYPE html>
<html>
    <head>
        <title>Dropbox MD5 Checker</title>
    </head>
    <body>
	<b>Новый поиск:</b><br />
        <form method="post" action="/">
            %setdefault('path', '/')
            %setdefault('extensions', '.doc, .txt') 
            <input type="text" name="path" value="{{path}}"/><br />
            <input type="text" name="extensions" value="{{extensions}}"/><br />
            <input type="submit" value="Проверить">
        </form>
        %if defined('status'):
            <br />
            <b>Информация о задаче:</b><br />
            Task status: {{status}}<br />
	    Path: {{path}}<br />
            Extensions: {{extensions}}<br />
        %end
        %if defined('coincidences'):
            <br />
            <b>Совпадения:</b><br />
            %if coincidences:
                %for coincidence in coincidences:
		    &#9658;&emsp;
                    %for cpath in coincidence:
                        {{cpath}}&emsp;
                    %end
                    <br />
                %end
            %else:
                None
            %end
        %end
    </body>
</html>
'''

token_name = b'dropbox-auth-csrf-token'
secret_key = "secret key      "
redirect_link = 'https://check.amokrov.org/check'
def get_flow(session):
    return DBAuth('bn4hy3qqp8ysquo', '4d53zmc6n8ldvo4', redirect_link, session, token_name)

def get_flow_start():
    session = dict()
    start = get_flow(session).start()
    response.set_cookie('token', str(session[token_name]), secret=secret_key, 
        httponly=True, path='/', max_age=18000)
    return start

def get_flow_finish():
    return get_flow({token_name: request.get_cookie('token', secret=secret_key)}).finish(request.query)[0]

default_path = '/'
default_extensions = ['.doc', '.txt']

@route('/')
def index():
    return template(tpl)

@post('/')
def index_post():
    post_path = request.forms.path.strip()
    post_extensions = [extension.strip() for extension in request.forms.extensions.split(',')]
    if not len(post_path):
        post_path = default_path
    if not len(post_extensions) or not len(post_extensions[0]):
        post_extensions = default_extensions
    response.set_cookie('folder', post_path, secret=secret_key, httponly=True, path='/', max_age=18000)
    response.set_cookie('extensions', post_extensions, secret=secret_key, httponly=True, path='/', max_age=18000)
    redirect(get_flow_start())

@route('/check')
def check():
    post_path = request.get_cookie('folder', secret=secret_key)
    post_extensions = request.get_cookie('extensions', secret=secret_key)
    if post_path is None:
        post_path = default_path
    if post_extensions is None:
        post_extensions = default_extensions
    response.set_cookie('guid', check_task.delay(
                                    DBClient(get_flow_finish()), 
                                    post_path,
                                    post_extensions).id, 
        secret=secret_key, httponly=True, path='/', max_age=18000)
    redirect('/result')

@route('/result')
def result():
    post_path = request.get_cookie('folder', secret=secret_key)
    post_extensions = request.get_cookie('extensions', secret=secret_key)
    if post_path is None:
        post_path = default_path
    if post_extensions is None:
        post_extensions = default_extensions
    post_extensions = ", ".join(post_extensions)
    guid = request.get_cookie('guid', secret=secret_key)
    if guid is None:
        redirect('/')
    results = check_task.AsyncResult(guid)
    if results is None:
        return template(tpl, status='does not exist', path=post_path, extensions=post_extensions)
    if not results.ready():
        return template(tpl, status=results.status, path=post_path, extensions=post_extensions)
    return template(tpl, status=results.status, path=post_path, extensions=post_extensions, coincidences=results.get())

run(host='localhost', port=8081, reloader=True, debug=True, server='cherrypy')
