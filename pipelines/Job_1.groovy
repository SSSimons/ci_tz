properties([
    disableConcurrentBuilds(),
    buildDiscarder(logRotator(numToKeepStr: '10')),
    copyArtifactPermission('Job_2'),
    pipelineTriggers([pollSCM('H/2 * * * *')])
])
timeout(time: 20, unit: 'MINUTES') {
    node {
        stage('Checkout master') {
            dir('project') {
                deleteDir()
                checkout([$class: 'GitSCM',
                    branches: [[name: '*/master']],
                    userRemoteConfigs: [[url: env.REPO_URL, credentialsId: 'git-ssh']],
                    extensions: [[$class: 'MessageExclusion', excludedMessage: '(?s)^\\[ci-cleanup\\].*']]
                ])
                sh 'git log -1 --oneline'
            }
        }
        stage('Archive exact checkout') {
            sh 'tar -czf project.tar.gz -C project .'
            archiveArtifacts artifacts: 'project.tar.gz', fingerprint: true
        }
    }
    // Вызов вне node: освобождаем executor перед ожиданием следующей job.
    stage('Run Job_2') {
        build job: 'Job_2', parameters: [string(name: 'SOURCE_BUILD', value: env.BUILD_NUMBER)],
            wait: true, propagate: true
    }
}
