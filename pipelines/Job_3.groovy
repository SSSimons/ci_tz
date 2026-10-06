properties([
    disableConcurrentBuilds(),
    buildDiscarder(logRotator(numToKeepStr: '10')),
    parameters([string(name: 'SOURCE_BUILD', defaultValue: '', description: 'Exact Job_2 build')])
])
if (!(params.SOURCE_BUILD ==~ /[0-9]+/)) error('SOURCE_BUILD must be a Job_2 build number')
timeout(time: 10, unit: 'MINUTES') {
    node {
        deleteDir()
        stage('Receive Job_2 changes') {
            copyArtifacts projectName: 'Job_2', selector: specific(params.SOURCE_BUILD),
                filter: 'project.tar.gz', fingerprintArtifacts: true
            sh 'mkdir project && tar -xzf project.tar.gz -C project'
        }
        dir('project') {
            stage('Commit and push to master') {
                int unchanged = sh(script: 'git diff --cached --quiet', returnStatus: true)
                if (unchanged == 0) {
                    echo 'Selected files are already absent; no commit or push needed.'
                } else if (unchanged == 1) {
                    sh '''
                        git config user.name "$GIT_AUTHOR_NAME"
                        git config user.email "$GIT_AUTHOR_EMAIL"
                        git commit -m "[ci-cleanup] Remove selected files"
                    '''
                    sshagent(credentials: ['git-ssh']) {
                        withEnv(['GIT_SSH_COMMAND=ssh -o BatchMode=yes -o StrictHostKeyChecking=yes']) {
                            sh 'git push origin HEAD:refs/heads/master'
                        }
                    }
                    sh 'git log -1 --oneline'
                } else {
                    error('Cannot inspect staged changes')
                }
            }
        }
    }
}
