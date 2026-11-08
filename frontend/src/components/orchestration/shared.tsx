import { useState } from 'react'
import { SkillToolResult } from '../../api/agentSkillsApi'

export const confidenceLabels: Record<string, string> = { ALTO: 'Alta', MEDIO: 'Média', BAIXO: 'Baixa' }

// Média medida em produção (11/2026) com openai/gpt-5-mini. Usada antes de haver
// tempo real da execução para calcular a estimativa.
export const DEFAULT_SECONDS_PER_SKILL = 45

// Mesmo valor padrão de ORCHESTRATION_MAX_PARALLEL_SKILLS no backend. Durante a
// execução, vale o que vier no evento de início.
export const DEFAULT_MAX_PARALLEL_SKILLS = 3

export function estimateRunSeconds(
  skillCount: number,
  secondsPerSkill = DEFAULT_SECONDS_PER_SKILL,
  maxParallel = DEFAULT_MAX_PARALLEL_SKILLS,
) {
  return Math.round(Math.ceil(skillCount / maxParallel) * secondsPerSkill)
}

export function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function formatEstimate(totalSeconds: number) {
  if (totalSeconds < 60) return 'menos de 1 min'
  return `cerca de ${Math.ceil(totalSeconds / 60)} min`
}

export const domainLabels: Record<string, string> = {
  codigo_legado: 'Código Legado',
  regras_negocio: 'Regras de Negócio',
  arquitetura_software: 'Arquitetura de Software',
  seguranca_informacao: 'Segurança da Informação',
  qualidade_testes: 'Qualidade e Testes',
  observabilidade_monitoramento: 'Observabilidade e Monitoramento',
  performance_escalabilidade: 'Performance e Escalabilidade',
  dados_privacidade: 'Dados e Privacidade (LGPD)',
  infraestrutura_devops: 'Infraestrutura e DevOps',
  apis_integracoes: 'APIs e Integrações',
}

// Área livre sem rótulo conhecido: "game_design" vira "Game design".
export function domainLabel(domain: string): string {
  if (domainLabels[domain]) return domainLabels[domain]
  const text = domain.replace(/_/g, ' ').trim()
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// A área agora é texto livre, então um marcador só é reconhecido se for uma área
// conhecida: o resumo vem do modelo e pode trazer colchetes por outros motivos.
export function parseSynthesisByDomain(text: string, domains: string[] = []): Array<{ domain: string; text: string }> {
  const known = [...new Set([...Object.keys(domainLabels), ...domains])]
  const alternatives = known.map((domain) => domain.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const matches = [...text.matchAll(new RegExp(`\\[(${alternatives})\\]\\s*`, 'g'))]
  if (matches.length === 0) return [{ domain: '', text }]

  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length
    return { domain: match[1], text: text.slice(start, end).trim() }
  })
}

export function SynthesisByDomain({ text, domains }: { text: string; domains?: string[] }) {
  const parts = parseSynthesisByDomain(text, domains)
  return (
    <div className="workspace-synthesis-list">
      {parts.map((part, index) => (
        <div key={`${part.domain}-${index}`} className="workspace-synthesis-item">
          {part.domain && <span className="workspace-synthesis-domain">{domainLabel(part.domain)}</span>}
          <p>{part.text}</p>
        </div>
      ))}
    </div>
  )
}

function slugify(text: string): string {
  return (
    text
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '') || 'trecho'
  )
}

function CodeBlock({ code, filenameHint }: { code: string; filenameHint: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard indisponível (ex.: contexto não seguro) -- falha silenciosa,
      // o usuário ainda pode selecionar e copiar o texto manualmente.
    }
  }

  function handleDownload() {
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${slugify(filenameHint)}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="workspace-code-block-wrap">
      <div className="workspace-code-block-toolbar">
        <button type="button" className="workspace-code-block-action" onClick={handleCopy}>
          {copied ? '✓ Copiado' : 'Copiar'}
        </button>
        <button type="button" className="workspace-code-block-action" onClick={handleDownload}>
          Baixar
        </button>
      </div>
      <pre className="workspace-code-block">
        <code>{code}</code>
      </pre>
    </div>
  )
}

type SkillResultCardProps = {
  result: SkillToolResult
  // Na resposta final, os cards começam fechados e o painel controla abrir e fechar.
  // Nas perguntas de acompanhamento, continuam sempre abertos.
  collapsible?: boolean
  open?: boolean
  onToggle?: () => void
}

export function SkillResultCard({ result, collapsible = false, open = true, onToggle }: SkillResultCardProps) {
  const [findingsOpen, setFindingsOpen] = useState(false)
  const expanded = !collapsible || open

  const heading = (
    <>
      <div>
        <strong>{result.agente_emissor.nome}</strong>
        <span className="workspace-skill-card-domain">{domainLabel(result.agente_emissor.dominio)}</span>
      </div>
      <span className={`workspace-confidence-pill workspace-confidence-${result.governanca.nivel_confianca.toLowerCase()}`}>
        {confidenceLabels[result.governanca.nivel_confianca]}
      </span>
    </>
  )

  return (
    <article className={`workspace-execution-skill-card${collapsible ? ' workspace-skill-card-collapsible' : ''}`}>
      {collapsible ? (
        <button type="button" className="workspace-skill-card-toggle" aria-expanded={expanded} onClick={onToggle}>
          <span aria-hidden="true" className="workspace-skill-card-chevron">{expanded ? '▾' : '▸'}</span>
          {heading}
        </button>
      ) : (
        <header>{heading}</header>
      )}
      {expanded && <SkillResultBody result={result} findingsOpen={findingsOpen} onToggleFindings={() => setFindingsOpen((value) => !value)} />}
    </article>
  )
}

function SkillResultBody({
  result,
  findingsOpen,
  onToggleFindings,
}: {
  result: SkillToolResult
  findingsOpen: boolean
  onToggleFindings: () => void
}) {
  const findings = result.analise_estruturada.descobertas_tecnicas
  return (
    <>
      <p>{result.analise_estruturada.resumo_executivo}</p>

      {findings.length > 0 && (
        <>
          <button
            type="button"
            className="workspace-findings-toggle"
            onClick={onToggleFindings}
            aria-expanded={findingsOpen}
          >
            {findingsOpen ? '▾' : '▸'} {findings.length} achado{findings.length === 1 ? '' : 's'} técnico{findings.length === 1 ? '' : 's'}
          </button>
          {findingsOpen && (
            <div className="workspace-findings">
              {findings.map((finding, findingIndex) => (
                <div key={findingIndex} className="workspace-finding">
                  <strong>{finding.item_identificado}</strong>
                  <p>{finding.descricao_detalhada}</p>
                  {finding.trecho_referenciado && (
                    <CodeBlock code={finding.trecho_referenciado} filenameHint={finding.item_identificado} />
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <small className="workspace-skill-card-justification">{result.governanca.justificativa_confianca}</small>
    </>
  )
}
