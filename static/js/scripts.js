document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.url-tile, .tool-tile, .script-tile');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });

    // Добавление URL
    document.getElementById('saveUrl')?.addEventListener('click', function() {
        const form = document.getElementById('addUrlForm');
        const formData = new FormData(form);

        fetch('/', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            }
        });
    });

    // Редактирование URL
    document.querySelectorAll('.edit-url').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const url = Array.from(document.querySelectorAll('#urlsList .list-group-item'))
                .find(item => item.querySelector('.delete-url').dataset.id === id);
            const [name, rest] = url.textContent.trim().split(' (');
            const urlValue = rest.slice(0, -1);
            const form = document.getElementById('editUrlForm');
            form.querySelector('[name="name"]').value = name;
            form.querySelector('[name="url"]').value = urlValue;
            form.querySelector('[name="id"]').value = id;
        });
    });

    document.getElementById('updateUrl')?.addEventListener('click', function() {
        const form = document.getElementById('editUrlForm');
        const formData = new FormData(form);

        fetch('/', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            }
        });
    });

    // Удаление URL
    document.querySelectorAll('.delete-url').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const urlId = this.dataset.id;
            fetch('/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `action=delete&id=${urlId}`
            })
                .then(response => response.json())
                .then(data => {
                if (data.status === 'success') {
                    location.reload();
                }
            });
        });
    });

    // Добавление скрипта
    document.getElementById('saveScript')?.addEventListener('click', function() {
        const form = document.getElementById('addScriptForm');
        const formData = new FormData(form);

        fetch('/scripts', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            }
        });
    });

    // Редактирование скрипта
    document.querySelectorAll('.edit-script').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const script = Array.from(document.querySelectorAll('#scriptsList .list-group-item'))
                .find(item => item.querySelector('.delete-script').dataset.id === id);
            const [name, desc] = script.textContent.trim().split(' - ');
            if (name.endsWith('.html')) {
                fetch(`/get_html_content/${id}`)
                    .then(response => response.json())
                    .then(data => {
                    if (data.status === 'success') {
                        editor.setValue(data.content);
                        document.getElementById('editHtmlId').value = id;
                    }
                });
            } else {
                const form = document.getElementById('editScriptForm');
                form.querySelector('[name="name"]').value = name;
                form.querySelector('[name="desc"]').value = desc;
                form.querySelector('[name="id"]').value = id;
            }
        });
    });

    document.getElementById('updateScript')?.addEventListener('click', function() {
        const form = document.getElementById('editScriptForm');
        const formData = new FormData(form);

        fetch('/scripts', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            }
        });
    });

    document.getElementById('saveHtml')?.addEventListener('click', function() {
        const form = document.getElementById('editHtmlForm');
        const formData = new FormData(form);
        formData.set('content', editor.getValue());

        fetch('/scripts', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            }
        });
    });

    // Удаление скрипта
    document.querySelectorAll('.delete-script').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const scriptId = this.dataset.id;
            fetch('/scripts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `action=delete&id=${scriptId}`
            })
                .then(response => response.json())
                .then(data => {
                if (data.status === 'success') {
                    location.reload();
                }
            });
        });
    });

    // Загрузка скрипта
    document.getElementById('uploadScript')?.addEventListener('click', function() {
        const form = document.getElementById('uploadScriptForm');
        const formData = new FormData(form);

        fetch('/scripts', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(data.message);
            }
        });
    });

    // Запуск инструментов
    document.querySelectorAll('.run-btn[data-type="tool"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const name = this.dataset.name;
            const url = `/run_tool/${name}`;

            btn.disabled = true;
            btn.textContent = 'Running...';

            fetch(url, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                const outputModal = new bootstrap.Modal(document.getElementById('outputModal'));
                document.getElementById('outputText').textContent =
                data.status === 'success' ? data.output : data.message;
                outputModal.show();
            })
                .finally(() => {
                btn.disabled = false;
                btn.textContent = 'Run';
            });
        });
    });

    // Запуск скриптов
    document.querySelectorAll('.run-btn[data-type="script"]').forEach(btn => {
        btn.addEventListener('click', function() {
            const name = this.dataset.name;
            document.getElementById('runScriptName').value = name;
            document.getElementById('scriptOutput').textContent = '';
        });
    });

    document.getElementById('executeScript')?.addEventListener('click', function() {
        const form = document.getElementById('runScriptForm');
        const formData = new FormData(form);
        const scriptName = formData.get('script_name');
        const url = `/run_script/${scriptName}`;

        fetch(url, {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            document.getElementById('scriptOutput').textContent =
            data.status === 'success' ? data.output : data.message;
        });
    });

    // Логин админа
    document.getElementById('loginForm')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);

        fetch('/admin', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(data.message);
            }
        });
    });

    // Выход из админки
    document.querySelectorAll('#logoutBtn').forEach(btn => {
        btn.addEventListener('click', function() {
            fetch('/logout', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                if (data.status === 'success') {
                    location.reload();
                }
            });
        });
    });

    // Очистка логов
    document.getElementById('clearLogsBtn')?.addEventListener('click', function() {
        fetch('/clear_logs', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(data.message);
            }
        });
    });

    // Загрузка иконки
    document.getElementById('uploadIcon')?.addEventListener('click', function() {
        const form = document.getElementById('addIconForm');
        const formData = new FormData(form);
        formData.append('action', 'add_icon');

        fetch('/admin', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert(data.message);
            }
        });
    });

    // Сортировка
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.dataset.type;
            const list = document.getElementById(type === 'urls' ? 'urlsList' : 'scriptsList');
            const items = Array.from(list.children);
            items.sort((a, b) => a.dataset.name.localeCompare(b.dataset.name));
            items.forEach(item => list.appendChild(item));
        });
    });
});
