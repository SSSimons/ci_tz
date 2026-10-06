# Jenkins: три автоматически связанных job

Учебный стенд для задания CI/CD. На Linux-сервере запускается Jenkins в Docker, а исходный код хранится в отдельном Git-репозитории с веткой `master`.

## Что выполняется

1. **Job_1** клонирует `master` в локальный workspace Jenkins и сохраняет архив проекта, включая `.git`.
2. **Job_2** получает архив конкретной сборки Job_1, удаляет один или два заданных файла и сохраняет результат.
3. **Job_3** получает результат конкретной сборки Job_2, создаёт коммит и отправляет его в `master` исходного репозитория.

Первый запуск происходит автоматически после создания job. Далее Job_1 опрашивает Git примерно каждые две минуты. Job_2 и Job_3 запускаются предыдущей job только при её успехе. Ручной запуск через интерфейс не требуется.

Коммиты с префиксом `[ci-cleanup]` исключены из SCM polling, чтобы собственный push Jenkins не запускал бесконечную цепочку. Если выбранные файлы уже отсутствуют, новая сборка завершается без коммита. Этот префикс зарезервирован для Jenkins.

## 1. Подготовка сервера

Нужны Git, Python 3.9+, OpenSSH client, Docker Engine и Docker Compose v2 с поддержкой `up --wait`. Для Ubuntu/Debian базовые утилиты можно установить так:

```bash
sudo apt update
sudo apt install -y git python3 openssh-client unzip
```

Docker и плагин Compose установите по инструкции для своей ОС: https://docs.docker.com/engine/install/ubuntu/ .

Распакуйте архив и подготовьте конфигурацию:

```bash
unzip jenkins-ci-lab.zip
cd jenkins-ci-lab
bash deploy.sh --prepare
```

Команда создаст `.env`, случайный пароль администратора и SSH-ключ Jenkins. При повторном выполнении существующие значения сохраняются.

## 2. Репозиторий

Используйте отдельный репозиторий для тестового задания: цепочка действительно удаляет заданные файлы и отправляет коммит. Ветка должна называться `master`. В `demo/` есть небольшой пример проекта и два файла для удаления.

Если репозиторий ещё пустой, отправьте в него пример со своей рабочей машины или сервера, где настроен ваш доступ к Git:

```bash
cd demo
git init -b master
git config user.name "Your Name"
git config user.email "you@example.com"
git add .
git commit -m "Initial demo project"
git remote add origin git@github.com:YOUR_USER/YOUR_REPO.git
git push -u origin master
cd ..
```

Замените URL на свой. В GitHub добавьте содержимое `secrets/git_key.pub` в **Settings → Deploy keys** репозитория и включите **Allow write access**. Для GitLab можно использовать deploy key с правом записи. Jenkins должен иметь право push в `master`; правила защиты ветки должны разрешать такой push.

Заполните `.env`:

```dotenv
REPO_URL=git@github.com:YOUR_USER/YOUR_REPO.git
DELETE_FILES='["obsolete.txt", "legacy.txt"]'
JENKINS_ADMIN_USER=admin
GIT_AUTHOR_NAME=Jenkins CI
GIT_AUTHOR_EMAIL=ci@example.com
```

`DELETE_FILES` — JSON-список из одного или двух точных относительных путей. Каталоги, `.git`, выход за пределы проекта и символьные ссылки не допускаются. Маски вроде `*.txt` не раскрываются.

## 3. Ключ сервера Git

Создайте `secrets/known_hosts` с проверенными SSH host keys вашего Git-сервера. Для GitHub можно сначала получить ключи:

```bash
ssh-keyscan -H github.com > secrets/known_hosts
ssh-keygen -lf secrets/known_hosts
```

Сверьте отпечатки с https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints . Для другого Git-сервера используйте его хост и отпечатки, полученные у администратора. Сам `ssh-keyscan` подлинность сервера не проверяет.

## 4. Запуск Jenkins

```bash
sudo bash deploy.sh
```

Если текущему пользователю уже разрешён доступ к Docker, `sudo` не нужен. Скрипт соберёт образ, запустит контейнер и дождётся доступности Jenkins. Первый запуск может занять несколько минут из-за скачивания образа и плагинов.

Откройте http://127.0.0.1:8085 . Логин — значение `JENKINS_ADMIN_USER`, пароль:

```bash
cat secrets/admin_password
```

Jenkins слушает только loopback сервера. Для доступа с другой машины используйте SSH-туннель:

```bash
ssh -L 8085:127.0.0.1:8085 USER@SERVER
```

Job_1, Job_2 и Job_3 создаются автоматически вместе с Git credentials. Первый запуск Job_1 ставится в очередь автоматически. В интерфейсе можно следить за статусами и **Console Output**.

## 5. Как проверить результат

- Все три job завершились успешно.
- В `master` появился коммит `[ci-cleanup] Remove selected files`.
- `obsolete.txt` и `legacy.txt` удалены; `app.py` и `README.md` остались.
- Через несколько интервалов polling новые сборки из-за коммита Jenkins не появляются.
- Новый обычный коммит в `master` автоматически запускает очередную цепочку. Чтобы снова проверить удаление, верните два тестовых файла таким коммитом.

## Реализация и диагностика

- `init/01-setup.groovy` — пользователь, права доступа, SSH credentials и создание трёх Pipeline job.
- `pipelines/Job_*.groovy` — checkout, передача артефактов, последовательный запуск и push.
- `scripts/remove_files.py` — проверка путей и `git rm` выбранных файлов.
- Данные Jenkins сохраняются в Docker volume `jenkins_home`.
- Вызовы следующей job находятся вне `node`, поэтому единственный executor освобождается перед ожиданием следующей сборки.
- Обычный `git push` не перезаписывает историю. Если `master` изменился во время цепочки, push отклоняется; следующий checkout должен взять актуальный `master`. Причину провала видно в Console Output.
- Если запись в `master` з апрещена или SSH-ключ не имеет доступа, исправьте права Git; сбой не маскируется.
- При перезапуске конфигурация трёх учебных job обновляется из файлов образа. Изменения в интерфейсе этих job могут быть заменены.
- Архивы включают `.git` и содержимое проекта. Стенд предназначен для отдельного тестового репозитория без секретов.

Логи и остановка:

```bash
sudo docker compose logs --tail=100 jenkins
sudo docker compose down
```

`down` без `--volumes` сохраняет настройки и историю. После обычного перезапуска начальная сборка повторно не ставится в очередь; polling продолжает работу.

## Локальная проверка логики Git

```bash
python3 -m unittest discover -s tests -v
bash -n deploy.sh bootstrap.sh
```

Тесты используют временный bare-репозиторий: проверяют передачу проекта между workspace, удаление, commit/push, повторное выполнение, защиту путей и отклонение конфликтующего push. Они не запускают Jenkins. Полный запуск контейнера и работу SCM polling нужно проверить на сервере с Docker.
