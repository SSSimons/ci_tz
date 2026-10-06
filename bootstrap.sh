set -euo pipefail
for file in admin_password git_key known_hosts; do
  if [[ ! -s "/run/ci-secrets/$file" ]]; then
    echo "Отсутствует secrets/$file" >&2
    exit 1
  fi
done
install -d -o jenkins -g jenkins -m 700 "$JENKINS_HOME/.bootstrap" "$JENKINS_HOME/.ssh"
install -o jenkins -g jenkins -m 600 /run/ci-secrets/admin_password "$JENKINS_HOME/.bootstrap/admin_password"
install -o jenkins -g jenkins -m 600 /run/ci-secrets/git_key "$JENKINS_HOME/.bootstrap/git_key"
install -o jenkins -g jenkins -m 600 /run/ci-secrets/known_hosts "$JENKINS_HOME/.ssh/known_hosts"
exec gosu jenkins /usr/bin/tini -- /usr/local/bin/jenkins.sh
