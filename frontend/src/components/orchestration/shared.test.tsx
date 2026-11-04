import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { SkillToolResult } from '../../api/agentSkillsApi'
import {
  estimateRunSeconds,
  formatElapsed,
  formatEstimate,
  parseSynthesisByDomain,
  SkillResultCard,
  SynthesisByDomain,
} from './shared'

describe('estimateRunSeconds', () => {
  it('conta por rodadas, porque até o limite de skills roda ao mesmo tempo', () => {
    expect(estimateRunSeconds(3, 40, 3)).toBe(40)
    expect(estimateRunSeconds(4, 40, 3)).toBe(80)
    expect(estimateRunSeconds(10, 40, 3)).toBe(160)
  })

  it('não estima tempo quando não falta nenhuma skill', () => {
    expect(estimateRunSeconds(0, 40, 3)).toBe(0)
  })
})

describe('formatação de tempo', () => {
  it('mostra o tempo decorrido em minutos e segundos', () => {
    expect(formatElapsed(0)).toBe('00:00')
    expect(formatElapsed(65)).toBe('01:05')
    expect(formatElapsed(600)).toBe('10:00')
  })

  it('arredonda a estimativa para cima, para não prometer menos do que leva', () => {
    expect(formatEstimate(59)).toBe('menos de 1 min')
    expect(formatEstimate(60)).toBe('cerca de 1 min')
    expect(formatEstimate(61)).toBe('cerca de 2 min')
  })
})

describe('parseSynthesisByDomain', () => {
  it('separa a síntese por área', () => {
    expect(parseSynthesisByDomain('[codigo_legado] Trecho A. [regras_negocio] Trecho B.')).toEqual([
      { domain: 'codigo_legado', text: 'Trecho A.' },
      { domain: 'regras_negocio', text: 'Trecho B.' },
    ])
  })

  it('reconhece uma área livre só quando ela participou da análise', () => {
    const text = '[Contabilidade] Impacto fiscal.'

    expect(parseSynthesisByDomain(text, ['Contabilidade'])).toEqual([{ domain: 'Contabilidade', text: 'Impacto fiscal.' }])
    expect(parseSynthesisByDomain(text)).toEqual([{ domain: '', text }])
  })

  it('não confunde colchetes do modelo com marcador de área', () => {
    const text = 'Altere a chave [config] do arquivo.'

    expect(parseSynthesisByDomain(text)).toEqual([{ domain: '', text }])
  })

  it('aceita caracteres especiais no nome de uma área livre', () => {
    expect(parseSynthesisByDomain('[C++ (legado)] Trecho.', ['C++ (legado)'])).toEqual([
      { domain: 'C++ (legado)', text: 'Trecho.' },
    ])
  })
})

describe('SynthesisByDomain', () => {
  it('mostra o nome da área sem o marcador', () => {
    render(<SynthesisByDomain text="[codigo_legado] Trecho A. [Contabilidade] Trecho B." domains={['Contabilidade']} />)

    expect(screen.getByText('Código Legado')).toBeInTheDocument()
    expect(screen.getByText('Contabilidade')).toBeInTheDocument()
    expect(screen.queryByText(/\[Contabilidade\]/)).not.toBeInTheDocument()
  })
})

describe('SkillResultCard', () => {
  const result: SkillToolResult = {
    trace_id: 'TRC-1',
    agente_emissor: { nome: 'Skill de Impostos', versao_prompt: null, dominio: 'Contabilidade' },
    analise_estruturada: {
      resumo_executivo: 'Resumo da análise.',
      descobertas_tecnicas: [
        { item_identificado: 'Alíquota fixa', descricao_detalhada: 'A alíquota está no código.', trecho_referenciado: 'TAXA = 0.2' },
      ],
      impactos_mapeados: [],
    },
    governanca: { nivel_confianca: 'MEDIO', justificativa_confianca: 'Poucas fontes.', referencias_catalogo: [] },
  }

  it('mostra a área livre e o nível de confiança', () => {
    render(<SkillResultCard result={result} />)

    expect(screen.getByText('Contabilidade')).toBeInTheDocument()
    expect(screen.getByText('Média')).toBeInTheDocument()
  })

  it('só abre os achados técnicos a pedido', async () => {
    const user = userEvent.setup()
    render(<SkillResultCard result={result} />)
    expect(screen.queryByText('A alíquota está no código.')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /1 achado técnico/ }))

    expect(screen.getByText('A alíquota está no código.')).toBeInTheDocument()
    expect(screen.getByText('TAXA = 0.2')).toBeInTheDocument()
  })

  it('não mostra o botão de achados quando não há nenhum', () => {
    const empty = { ...result, analise_estruturada: { ...result.analise_estruturada, descobertas_tecnicas: [] } }
    render(<SkillResultCard result={empty} />)

    expect(screen.queryByRole('button', { name: /achado/ })).not.toBeInTheDocument()
  })
})
