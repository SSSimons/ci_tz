FROM jenkins/jenkins:lts-jdk21
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client python3 curl gosu
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY init/ /usr/share/jenkins/ref/init.groovy.d/
COPY pipelines/ /opt/ci-lab/pipelines/
COPY scripts/ /opt/ci-lab/scripts/
COPY bootstrap.sh /usr/local/bin/ci-bootstrap
RUN chmod +x /usr/local/bin/ci-bootstrap
ENTRYPOINT ["/usr/local/bin/ci-bootstrap"]
