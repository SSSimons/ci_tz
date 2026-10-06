#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ "${1:-}" == "--prepare" ]]; then
  command -v python3 >/dev/null
  command -v ssh-keygen >/dev/null
  umask 077
  mkdir -p secrets
  [[ -f .env ]] || cp .env.example .env
  if [[ ! -s secrets/admin_password ]]; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/admin_password
  fi
  if [[ ! -s secrets/git_key ]]; then
    ssh-keygen -t ed25519 -N '' -C 'jenkins-ci-lab' -f secrets/git_key
  fi
  echo 'Подготовлено. Заполните .env, добавьте secrets/git_key.pub в Git и создайте secrets/known_hosts.'
  exit 0
fi
command -v docker >/dev/null || { echo 'Установите Docker и Docker Compose (инструкция в README).' >&2; exit 1; }
docker compose version >/dev/null
test -f .env || { echo 'Сначала: bash deploy.sh --prepare' >&2; exit 1; }
for file in admin_password git_key known_hosts; do
  test -s "secrets/$file" || { echo "Отсутствует secrets/$file" >&2; exit 1; }
done
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 600
echo 'Jenkins: http://127.0.0.1:8085. Пароль хранится в: secrets/admin_password. Job_1 запускается автоматически.'
