import { Link } from 'react-router-dom'

export function PrivacyPage() {
  return (
    <main className="workspace-page workspace-page-narrow workspace-privacy">
      <h1>Política de privacidade</h1>
      <p>
        A Flav.IA é um projeto acadêmico, uma Prova de Conceito do Trabalho de Conclusão de Curso da autora. Esta página
        explica, em linguagem direta, como ele trata os seus dados, conforme a LGPD (Lei nº 13.709/2018).
      </p>
      <p>
        <strong>Não envie dados pessoais de terceiros, segredos ou informações confidenciais</strong> nas solicitações e nos
        anexos.
      </p>

      <h2>Dados que guardamos</h2>
      <ul>
        <li>Conta: nome, e-mail, senha protegida por hash e, se usar login social, o identificador do GitHub ou do Google.</li>
        <li>Sessão e auditoria: endereço IP, navegador, data das ações e eventos de segurança.</li>
        <li>Uso: solicitações, anexos, Agent Skills, comitês, respostas, arquivos gerados e as avaliações que você faz das respostas.</li>
      </ul>

      <h2>Para que usamos</h2>
      <p>Para autenticar você, executar as análises que você pede, manter a rastreabilidade delas e proteger o sistema.</p>

      <h2>Com quem compartilhamos</h2>
      <ul>
        <li>
          OpenRouter e os provedores de modelo de IA: recebem o texto da solicitação e dos anexos para gerar a análise. E-mails,
          senhas, tokens e chaves reconhecidos são mascarados antes do envio, mas essa detecção não pega todo dado pessoal.
        </li>
        <li>Microsoft Azure: hospeda o site e o banco de dados.</li>
        <li>Gmail: envia os e-mails de recuperação de senha e de código de acesso.</li>
        <li>GitHub e Google: somente se você escolher entrar com essas contas.</li>
      </ul>

      <h2>Cookies</h2>
      <p>Só os necessários para a sessão e para a proteção contra CSRF. Não há cookies de publicidade nem de análise de uso.</p>

      <h2>Por quanto tempo</h2>
      <p>Não há prazo automático de exclusão: os dados ficam enquanto a Prova de Conceito estiver no ar ou até você excluir a conta.</p>

      <h2>Seus direitos</h2>
      <p>
        Em <Link to="/account">Minha conta</Link>, você corrige o nome e exclui a conta. A exclusão desativa o acesso e remove o
        nome e o e-mail. O histórico de solicitações, skills e comitês permanece, sem ficar atribuído a você. Para outros pedidos,
        abra uma{' '}
        <a href="https://github.com/FlaviaAtonieli/multi-agent-ecosystem/issues" target="_blank" rel="noreferrer">
          issue no repositório do projeto
        </a>
        , sem colocar dados pessoais nela.
      </p>

      <p>
        <Link to="/login">Voltar</Link>
      </p>
    </main>
  )
}
