FROM jenkins/jenkins:lts-jdk21
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client python3 curl gosu
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY init/ /usr/share/jenkins/ref/init.groovy.d/
COPY pipelines/ /opt/ci-lab/pipelines/
COPY scripts/ /opt/ci-lab/scripts/
COPY bootstrap.sh /usr/local/bin/ci-bootstrap
RUN python3 -c "from pathlib import Path; p=Path('/usr/local/bin/ci-bootstrap'); p.write_bytes(p.read_bytes().removeprefix(bytes.fromhex('efbbbf')).replace(bytes.fromhex('0d0a'), bytes.fromhex('0a')))" \
    && chmod +x /usr/local/bin/ci-bootstrap \
    && bash -n /usr/local/bin/ci-bootstrap
ENTRYPOINT ["/bin/bash", "/usr/local/bin/ci-bootstrap"]
