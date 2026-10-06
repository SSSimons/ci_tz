# 🚀 Jenkins CI/CD

Тестовое задание: автоматически скачать `master`, удалить 1–2 файла и отправить изменения обратно в Git.

## ⚙️ Три job

| Job | Действие |
| --- | --- |
| **Job_1** | Скачивает `master` и сохраняет архив проекта |
| **Job_2** | Получает архив и удаляет файлы из `DELETE_FILES` |
| **Job_3** | Создаёт коммит и делает push в `master` |

Первый запуск — после создания job. Далее Git проверяется примерно каждые две минуты. Следующая job запускается только при успехе предыдущей; коммиты `[ci-cleanup]` не запускают цепочку повторно.

## 🛠️ Подготовка

Нужны **Git, Python 3.9+, OpenSSH и Docker Compose v2** с поддержкой `up --wait`.

Из корня проекта:

```bash
bash deploy.sh --prepare
```

В GitHub добавь `secrets/git_key.pub` в **Settings → Deploy keys** репозитория с галочкой **Allow write access**. Ветка `master` должна существовать и разрешать push этим ключом.

Получить ключи сервера GitHub:

```bash
ssh-keyscan -H github.com > secrets/known_hosts
ssh-keygen -lf secrets/known_hosts
```

Сверь отпечатки с [документацией GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints).

## 📝 Настройки

Заполни `.env`. Пример для репозитория `ci_tz`, в котором находится весь этот комплект:

```dotenv
REPO_URL=git@github.com:YOUR_USER/ci_tz.git
DELETE_FILES='["demo/obsolete.txt", "demo/legacy.txt"]'
JENKINS_ADMIN_USER=admin
GIT_AUTHOR_NAME=Sim
GIT_AUTHOR_EMAIL=ci@tz.com
```

Замени `YOUR_USER` своим логином. Для своих файлов укажи их точные пути от корня Git-репозитория. Например, `first.txt` и `second.txt` должны реально находиться в нём перед первой проверкой. `.env` и `secrets/` исключены из Git.

## ▶️ Запуск

```bash
sudo bash deploy.sh
cat secrets/admin_password
```

Jenkins: **http://127.0.0.1:8085**. Логин — `admin`, пароль — из файла выше. Порт `8085` настроен и на сервере, и внутри контейнера.

Для доступа со своего компьютера открой на нём туннель:

```bash
ssh -N -L 8085:127.0.0.1:8085 USER@SERVER
```

Затем зайди на **http://localhost:8085**. Три job создаются автоматически.

## ✅ Проверка задания

- Все три job зелёные; подробности доступны в **Console Output**.
- В `master` появился коммит `[ci-cleanup] Remove selected files`.
- Выбранные файлы удалены, остальные остались.
- Верни тестовый файл обычным коммитом: цепочка должна запуститься автоматически.

Если файлы уже отсутствуют, новый коммит не создаётся. Поэтому при первом запуске проверь пути в `DELETE_FILES`. `demo/README.md` для работы не нужен.

## 🔎 Диагностика

```bash
sudo docker compose ps
sudo docker compose logs --tail=100 jenkins
python3 -m unittest discover -s tests -v
```

Тесты проверяют операции Git; для проверки самих job нужен работающий Jenkins. Настройки и история хранятся в volume `jenkins_home`. Остановка с сохранением данных: `sudo docker compose down`.

## 🤖 GitHub Actions

Файл `.github/workflows/ci.yml` запускает CI при push в `master` и pull request в эту ветку. После отправки файлов результат появится во вкладке **Actions → CI**.

Проверки: синтаксис Bash и Python, тесты Git, конфигурация Compose и сборка образа Jenkins. Сборка запускается после успешных проверок. Secrets для этого workflow не нужны.

Тестовые файлы создаются во временном репозитории, поэтому CI работает и после удаления файлов Job_2. Actions проверяет код и собирает образ; развёртывание и цепочка из трёх job выполняются отдельно в Jenkins.
