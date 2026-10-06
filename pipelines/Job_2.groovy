properties([
    disableConcurrentBuilds(),
    buildDiscarder(logRotator(numToKeepStr: '10')),
    copyArtifactPermission('Job_3'),
    parameters([string(name: 'SOURCE_BUILD', defaultValue: '', description: 'Exact Job_1 build')])
])
if (!(params.SOURCE_BUILD ==~ /[0-9]+/)) error('SOURCE_BUILD must be a Job_1 build number')
timeout(time: 10, unit: 'MINUTES') {
    node {
        deleteDir()
        stage('Receive Job_1 checkout') {
            copyArtifacts projectName: 'Job_1', selector: specific(params.SOURCE_BUILD),
                filter: 'project.tar.gz', fingerprintArtifacts: true
            sh 'mkdir project && tar -xzf project.tar.gz -C project'
        }
        stage('Delete selected files') {
            dir('project') {
                sh 'python3 /opt/ci-lab/scripts/remove_files.py'
                sh 'git status --short'
            }
        }
        stage('Archive changes') {
            sh 'tar -czf project.tar.gz -C project .'
            archiveArtifacts artifacts: 'project.tar.gz', fingerprint: true
        }
    }
    stage('Run Job_3') {
        build job: 'Job_3', parameters: [string(name: 'SOURCE_BUILD', value: env.BUILD_NUMBER)],
            wait: true, propagate: true
    }
}
