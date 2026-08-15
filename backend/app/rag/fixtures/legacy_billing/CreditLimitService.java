package br.com.legado.financeiro;

import java.math.BigDecimal;

/**
 * Servico de limite de credito.
 *
 * OBS (2011): nao mexer sem falar com o Ricardo. A regra do limite
 * global veio do sistema antigo (COBOL) e foi só "traduzida" pra Java,
 * ninguem sabe direito o motivo do valor de R$ 5.000,00.
 */
public class CreditLimitService {

    // TODO: isso deveria vir de configuracao, nao deveria estar fixo no codigo.
    private static final BigDecimal LIMITE_GLOBAL = new BigDecimal("5000.00");

    private CustomerRepository customerRepository;

    public CreditLimitService(CustomerRepository customerRepository) {
        this.customerRepository = customerRepository;
    }

    /**
     * Retorna o limite de credito do cliente.
     *
     * Hoje o limite eh sempre o mesmo pra todo mundo (LIMITE_GLOBAL),
     * independente do segmento (varejo, atacado, corporativo). Isso é
     * usado em pelo menos 3 lugares do sistema:
     *   - tela de aprovacao de pedido (OrderApprovalController)
     *   - job noturno de recalculo de risco (RiskBatchJob)
     *   - relatorio financeiro mensal (FinanceReportService)
     *
     * Se mudar essa regra pra considerar segmento, TEM que atualizar
     * os 3 pontos acima, senao fica inconsistente.
     */
    public BigDecimal getLimiteCredito(String customerId) {
        Customer customer = customerRepository.findById(customerId);
        if (customer == null) {
            throw new IllegalArgumentException("Cliente nao encontrado: " + customerId);
        }

        // Regra atual: ignora completamente o segmento do cliente.
        // O campo customer.getSegmento() existe mas nunca é lido aqui.
        return LIMITE_GLOBAL;
    }

    /**
     * Verifica se um pedido pode ser aprovado com base no limite.
     * Usa getLimiteCredito(), entao herda a mesma limitacao (sem segmento).
     */
    public boolean podeAprovarPedido(String customerId, BigDecimal valorPedido) {
        BigDecimal limite = getLimiteCredito(customerId);
        BigDecimal totalUtilizado = customerRepository.getTotalUtilizado(customerId);
        BigDecimal disponivel = limite.subtract(totalUtilizado);
        return valorPedido.compareTo(disponivel) <= 0;
    }
}
