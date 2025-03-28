from flask import Flask, render_template, request, jsonify, session, send_from_directory, send_file
import subprocess
import os
import logging
from datetime import datetime
import shutil
import platform
import psutil
import json
from werkzeug.utils import secure_filename
from ldap3 import Server, Connection, ALL, SUBTREE
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Настройка логирования
logging.basicConfig(filename='sysadmin.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s')

LDAP_SERVER = 'ldap://айпи:389'  # Адрес контроллера домена
BASE_DN = 'DC=agrohold,DC=ru'  # Корневая DN
GROUP_DN = 'CN=имя группы,OU=Groups,OU=сайт,OU=сайт обл,DC=домен,DC=ru'  # Полный DN группы
BIND_DN = 'логин'  # Полный DN учётки
BIND_PASSWORD = 'пароль'  # Пароль от сервисной учётной записи


DATA_FILE = 'data.json'
SCRIPTS_DIR = 'scripts'
os.makedirs(SCRIPTS_DIR, exist_ok=True)

tabs = [
    {"name": "URLs", "route": "/"},
    {"name": "Tools", "route": "/tools"},
    {"name": "Scripts", "route": "/scripts"},
    {"name": "System Info", "route": "/system"},
    {"name": "Admin", "route": "/admin"}
]

# Загрузка данных из файла
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"urls": [], "scripts": [], "icons": ["globe", "github", "server", "gear", "cpu", "display", "hdd"]}

# Сохранение данных в файл
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

data = load_data()
urls_list = data["urls"]
scripts_list = data["scripts"]
available_icons = data["icons"]

def is_admin():
    return 'logged_in' in session

# Полная функция LDAP (не активирована)
def ldap_authenticate(username, password):
    try:
        # Подключение к серверу
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user=BIND_DN, password=BIND_PASSWORD, auto_bind=True)

        if conn.bind():
            # Поиск пользователя в каталоге
            conn.search(
                search_base=BASE_DN,
                search_filter=f'(sAMAccountName={username})',
                search_scope=SUBTREE,
                attributes=['cn', 'mail', 'memberOf']
            )

            if conn.entries:
                user_entry = conn.entries[0]
                groups = user_entry.memberOf
                print(f"User groups: {groups}")
                # Проверяем, состоит ли пользователь в группе
                if any(GROUP_DN.lower() in str(group).lower() for group in groups):
                    logging.info(f"LDAP: User {username} authenticated and is in WG IT 11")
                    conn.unbind()
                    return True
                else:
                    logging.warning(f"LDAP: User {username} is NOT in WG IT 11")
            conn.unbind()

        return False
    except Exception as e:
        logging.error(f"LDAP Error: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def urls():
    if request.method == 'POST' and is_admin():
        action = request.form.get('action')
        if action == 'add':
            new_url = {
                "id": len(urls_list) + 1,
                "name": request.form['name'],
                "url": request.form['url'],
                "icon": request.form.get('icon', 'globe')
            }
            urls_list.append(new_url)
            logging.info(f"Admin added URL: {new_url['name']} - {new_url['url']}")
        elif action == 'edit':
            url_id = int(request.form['id'])
            for url in urls_list:
                if url['id'] == url_id:
                    url.update({
                        "name": request.form['name'],
                        "url": request.form['url'],
                        "icon": request.form.get('icon', 'globe')
                    })
                    logging.info(f"Admin edited URL ID: {url_id}")
                    break
        elif action == 'delete':
            url_id = int(request.form['id'])
            urls_list[:] = [url for url in urls_list if url['id'] != url_id]
            logging.info(f"Admin deleted URL ID: {url_id}")
        save_data({"urls": urls_list, "scripts": scripts_list, "icons": available_icons})
        return jsonify({'status': 'success'})
    return render_template('urls.html', tabs=tabs, active_tab="URLs", urls=urls_list, icons=available_icons, is_admin=is_admin())

@app.route('/tools')
def tools():
    tools_list = [
        {"id": 1, "name": "Ping", "desc": "Check network connectivity", "command": "ping"},
        {"id": 2, "name": "Traceroute", "desc": "Trace network path", "command": "tracert" if os.name == 'nt' else "traceroute"},
        {"id": 3, "name": "Port Scanner", "desc": "Scan open ports", "command": "nmap"}
    ]
    for tool in tools_list:
        tool['available'] = bool(shutil.which(tool['command']))
    return render_template('tools.html', tabs=tabs, active_tab="Tools", tools=tools_list, is_admin=is_admin())

@app.route('/scripts', methods=['GET', 'POST'])
def scripts():
    if request.method == 'POST' and is_admin():
        action = request.form.get('action')
        if action == 'add':
            new_script = {
                "id": len(scripts_list) + 1,
                "name": request.form['name'],
                "desc": request.form['desc'],
                "path": f"scripts/{request.form['name']}",
                "icon": request.form.get('icon', 'gear')
            }
            scripts_list.append(new_script)
            if not os.path.exists(new_script['path']):
                ext = os.path.splitext(new_script['name'])[1]
                if ext == '.py':
                    with open(new_script['path'], 'w', encoding='utf-8') as f:
                        f.write('# Python script\nprint("Script initialized")')
                elif ext == '.ps1':
                    with open(new_script['path'], 'w', encoding='utf-8') as f:
                        f.write('# PowerShell script\nWrite-Output "Script initialized"')
                elif ext == '.html':
                    with open(new_script['path'], 'w', encoding='utf-8') as f:
                        f.write('<!DOCTYPE html>\n<html><body><h1>Script initialized</h1></body></html>')
            logging.info(f"Admin added script: {new_script['name']}")
        elif action == 'edit':
            script_id = int(request.form['id'])
            for script in scripts_list:
                if script['id'] == script_id:
                    old_path = script['path']
                    script.update({
                        "name": request.form['name'],
                        "desc": request.form['desc'],
                        "path": f"scripts/{request.form['name']}",
                        "icon": request.form.get('icon', 'gear')
                    })
                    if old_path != script['path'] and os.path.exists(old_path):
                        os.rename(old_path, script['path'])
                    logging.info(f"Admin edited script ID: {script_id}")
                    break
        elif action == 'delete':
            script_id = int(request.form['id'])
            script_to_delete = next((s for s in scripts_list if s['id'] == script_id), None)
            if script_to_delete and os.path.exists(script_to_delete['path']):
                os.remove(script_to_delete['path'])
            scripts_list[:] = [s for s in scripts_list if s['id'] != script_id]
            logging.info(f"Admin deleted script ID: {script_id}")
        elif action == 'upload':
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'message': 'No file part'})
            file = request.files['file']
            if file.filename == '':
                return jsonify({'status': 'error', 'message': 'No selected file'})
            if file and file.filename.endswith(('.py', '.ps1', '.html')):
                filename = secure_filename(file.filename)
                file_path = os.path.join(SCRIPTS_DIR, filename)
                file.save(file_path)
                new_script = {
                    "id": len(scripts_list) + 1,
                    "name": filename,
                    "desc": request.form.get('desc', 'Uploaded script'),
                    "path": file_path,
                    "icon": request.form.get('icon', 'gear')
                }
                scripts_list.append(new_script)
                logging.info(f"Admin uploaded script: {filename}")
        elif action == 'edit_html':
            script_id = int(request.form['id'])
            for script in scripts_list:
                if script['id'] == script_id and script['path'].endswith('.html'):
                    with open(script['path'], 'w', encoding='utf-8') as f:
                        f.write(request.form['content'])
                    logging.info(f"Admin edited HTML script ID: {script_id}")
                    break
        save_data({"urls": urls_list, "scripts": scripts_list, "icons": available_icons})
        return jsonify({'status': 'success'})

    for script in scripts_list:
        script['available'] = os.path.exists(script['path'])
    return render_template('scripts.html', tabs=tabs, active_tab="Scripts", scripts=scripts_list, icons=available_icons, is_admin=is_admin())

@app.route('/system')
def system_info():
    sys_info = {
        "os": platform.system() + " " + platform.release(),
        "cpu_usage": f"{psutil.cpu_percent(interval=1)}%",
        "ram_usage": f"{psutil.virtual_memory().percent}% ({psutil.virtual_memory().used / 1024**3:.1f}/{psutil.virtual_memory().total / 1024**3:.1f} GB)",
        "disk_usage": f"{psutil.disk_usage('/').percent}% ({psutil.disk_usage('/').used / 1024**3:.1f}/{psutil.disk_usage('/').total / 1024**3:.1f} GB)"
    }
    return render_template('system.html', tabs=tabs, active_tab="System Info", sys_info=sys_info, is_admin=is_admin())

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    encoding = 'cp1251' if os.name == 'nt' else 'utf-8'
    if 'logged_in' not in session:
        if request.method == 'POST':
            # Пока используем простой пароль, LDAP закомментирован
            #if request.form.get('username') == 'admin' and request.form.get('password') == 'admin123':
            # В будущем для LDAP:
            if ldap_authenticate(request.form.get('username'), request.form.get('password')):
                session['logged_in'] = True
                return jsonify({'status': 'success'})
            return jsonify({'status': 'error', 'message': 'Invalid credentials'})
        return render_template('admin_login.html', tabs=tabs, active_tab="Admin")

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_icon' and 'icon' in request.files:
            icon_file = request.files['icon']
            if icon_file and icon_file.filename.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                filename = secure_filename(icon_file.filename)
                icon_path = os.path.join('static/icons', filename)
                os.makedirs('static/icons', exist_ok=True)
                icon_file.save(icon_path)
                icon_name = os.path.splitext(filename)[0]
                if icon_name not in available_icons:
                    available_icons.append(icon_name)
                    save_data({"urls": urls_list, "scripts": scripts_list, "icons": available_icons})
                    logging.info(f"Admin added icon: {icon_name}")
                return jsonify({'status': 'success'})

    try:
        with open('sysadmin.log', 'r', encoding=encoding) as f:
            logs = f.readlines()
    except Exception as e:
        logs = [f"Error reading logs: {str(e)}"]
    return render_template('admin.html', tabs=tabs, active_tab="Admin", logs=logs, urls=urls_list, scripts=scripts_list, icons=available_icons)

@app.route('/run_tool/<tool_name>', methods=['POST'])
def run_tool(tool_name):
    try:
        args = []
        encoding = 'utf-8'
        env = os.environ.copy()
        env["LANG"] = "en_US.UTF-8"  # Для Unix систем
        if os.name == 'nt':
            # Для Windows используем cmd с перенаправлением вывода на английский
            if tool_name == "ping":
                args = ["cmd", "/c", "ping 8.8.8.8 -n 4"]
            elif tool_name == "tracert":
                args = ["cmd", "/c", "tracert 8.8.8.8"]
            else:
                args = [tool_name] + (["8.8.8.8", "-n", "4"] if tool_name == "ping" else ["8.8.8.8"])
            encoding = 'cp1252'  # Английская локаль Windows
        else:
            # Для Unix систем
            if tool_name == "ping":
                args = ["ping", "8.8.8.8", "-c", "4"]
            elif tool_name in ["tracert", "traceroute"]:
                args = ["traceroute", "8.8.8.8"]
            elif tool_name == "nmap":
                args = ["nmap", "-F", "localhost"]

        if not shutil.which(tool_name) and tool_name not in ["ping", "tracert"]:
            return jsonify({'status': 'error', 'message': f"{tool_name} not found"})

        result = subprocess.run(args, capture_output=True, text=True, encoding=encoding, errors='replace', timeout=10, env=env)
        output = result.stdout or result.stderr
        logging.info(f"Ran tool {tool_name}: {output[:100]}...")
        return jsonify({'status': 'success', 'output': output})
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Command timed out'})
    except Exception as e:
        logging.error(f"Error running tool {tool_name}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/run_script/<script_name>', methods=['POST'])
def run_script(script_name):
    try:
        script_path = f'scripts/{script_name}'
        if not os.path.exists(script_path):
            return jsonify({'status': 'error', 'message': f"Script {script_name} not found"})

        ext = os.path.splitext(script_name)[1]
        params = request.form.get('params', '').split()
        if ext == '.py':
            args = ['python', script_path] + params
        elif ext == '.ps1':
            args = ['powershell', '-File', script_path] + params
        elif ext == '.html':
            with open(script_path, 'r', encoding='utf-8') as f:
                return jsonify({'status': 'success', 'output': f.read()})
        else:
            return jsonify({'status': 'error', 'message': f"Unsupported script type: {ext}"})

        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8' if ext == '.py' else 'cp1252',
                                errors='replace', timeout=10)
        output = result.stdout or result.stderr
        logging.info(f"Ran script {script_name}: {output[:100]}...")
        return jsonify({'status': 'success', 'output': output})
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Script timed out'})
    except Exception as e:
        logging.error(f"Error running script {script_name}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download_script/<script_name>')
def download_script(script_name):
    if is_admin():
        script_path = f'scripts/{script_name}'
        if os.path.exists(script_path):
            return send_file(script_path, as_attachment=True)
        return jsonify({'status': 'error', 'message': 'Script not found'})
    return jsonify({'status': 'error', 'message': 'Unauthorized'})

@app.route('/get_html_content/<script_id>')
def get_html_content(script_id):
    if is_admin():
        script = next((s for s in scripts_list if str(s['id']) == script_id), None)
        if script and script['path'].endswith('.html'):
            with open(script['path'], 'r', encoding='utf-8') as f:
                return jsonify({'status': 'success', 'content': f.read()})
        return jsonify({'status': 'error', 'message': 'Script not found or not HTML'})
    return jsonify({'status': 'error', 'message': 'Unauthorized'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'status': 'success'})

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    if is_admin():
        try:
            open('sysadmin.log', 'w').close()
            logging.info("Logs cleared by admin")
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': 'Unauthorized'})

@app.route('/icons/<path:filename>')
def serve_icon(filename):
    return send_from_directory('static/icons', filename)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5005)
