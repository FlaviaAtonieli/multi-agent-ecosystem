package com.legacybilling.credit;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Suite de teste unico existente para CreditLimitService. Ver
 * test-coverage-audit.md para o levantamento completo de lacunas de
 * cobertura -- este arquivo so cobre o caminho padrao (cliente sem
 * SEGMENTO definido).
 */
class CreditLimitServiceTest {

    private final CreditLimitService service = new CreditLimitService(
        new CustomerRepository(TestDatabase.connection())
    );

    @Test
    void testLimiteFixoCincoMil() {
        // Unico cenario coberto: cliente sem SEGMENTO, limite fixo atual.
        double limite = service.getLimiteCredito("cliente-sem-segmento");
        assertEquals(5000.00, limite);
    }

    // TODO (registrado na auditoria de QA de 2023, nunca feito):
    // - testLimiteClienteCorporativo() -- nao existe, CR-2019-114 nunca
    //   ganhou um teste mesmo estando aprovada em comite.
    // - testLimiteClienteVarejoAltoRisco() -- nao existe.
    // - testLimiteConsistenteEntreOrderApprovalControllerERiskBatchJob() --
    //   nao existe nenhum teste que valide os dois consumidores retornando
    //   o mesmo valor para o mesmo cliente.
}
