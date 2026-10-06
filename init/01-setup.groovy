import jenkins.model.Jenkins
import hudson.model.Cause
import hudson.model.ParametersDefinitionProperty
import hudson.model.StringParameterDefinition
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey
import org.jenkinsci.plugins.gitclient.GitHostKeyVerificationConfiguration
import org.jenkinsci.plugins.gitclient.verifier.KnownHostsFileVerificationStrategy
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import groovy.json.JsonSlurper

Jenkins j = Jenkins.get()
def config = System.getenv()
if (!config.REPO_URL) throw new IllegalArgumentException('REPO_URL is required')
def files = new JsonSlurper().parseText(config.DELETE_FILES ?: '[]')
if (!(files instanceof List) || files.size() < 1 || files.size() > 2 || !files.every { it instanceof String && it }) {
    throw new IllegalArgumentException('DELETE_FILES must be a JSON list of 1 or 2 file paths')
}
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount(config.JENKINS_ADMIN_USER ?: 'admin',
    new File(j.rootDir, '.bootstrap/admin_password').text.trim())
j.setSecurityRealm(realm)
def authorization = new FullControlOnceLoggedInAuthorizationStrategy()
authorization.setAllowAnonymousRead(false)
j.setAuthorizationStrategy(authorization)
// Учебный стенд: выполнение job на встроенном узле, без доступа к Docker socket.
j.setNumExecutors(1)
j.setSystemMessage('CI/CD lab: master -> Job_1 -> Job_2 -> Job_3')

def store = SystemCredentialsProvider.getInstance().getStore()
def domain = Domain.global()
def existing = store.getCredentials(domain).find { it.id == 'git-ssh' }
if (existing) store.removeCredentials(domain, existing)
def keyFile = new File(j.rootDir, '.bootstrap/git_key')
def source = new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(keyFile.text)
store.addCredentials(domain, new BasicSSHUserPrivateKey(
    CredentialsScope.GLOBAL, 'git-ssh', 'git', source, '', 'CI repository SSH key'))
keyFile.delete()
def verification = j.getDescriptorByType(GitHostKeyVerificationConfiguration.class)
verification.setSshHostKeyVerificationStrategy(new KnownHostsFileVerificationStrategy())
verification.save()

boolean firstRun = j.getItem('Job_1') == null
['Job_1', 'Job_2', 'Job_3'].each { name ->
    def job = j.getItem(name)
    if (job == null) job = j.createProject(WorkflowJob.class, name)
    if (!(job instanceof WorkflowJob)) throw new IllegalStateException("${name} already exists with another type")
    job.setDefinition(new CpsFlowDefinition(new File("/opt/ci-lab/pipelines/${name}.groovy").text, true))
    if (name != 'Job_1') {
        job.addProperty(new ParametersDefinitionProperty(
            new StringParameterDefinition('SOURCE_BUILD', '', 'Exact upstream build number')))
    }
    job.setDescription("Automatically configured ${name}; source in /opt/ci-lab/pipelines")
    job.save()
}
j.save()
if (firstRun) {
    j.getItem('Job_1').scheduleBuild2(5, new Cause.RemoteCause('bootstrap', 'Initial automatic build'))
}
