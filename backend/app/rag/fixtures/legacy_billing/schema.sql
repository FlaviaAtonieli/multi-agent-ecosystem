-- Schema legado do módulo financeiro (fixture sintética para a PoC).
-- Convenções antigas: nomes em maiúsculo, sem FKs nomeadas, sem migrations versionadas.

CREATE TABLE CUSTOMER (
    ID VARCHAR(36) PRIMARY KEY,
    NOME VARCHAR(160) NOT NULL,
    EMAIL VARCHAR(160),
    SEGMENTO VARCHAR(20) DEFAULT 'VAREJO', -- VAREJO | ATACADO | CORPORATIVO. Adicionado em 2019, pouco usado.
    CRIADO_EM TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CUSTOMER_ORDER (
    ID VARCHAR(36) PRIMARY KEY,
    CUSTOMER_ID VARCHAR(36) NOT NULL REFERENCES CUSTOMER(ID),
    VALOR_TOTAL DECIMAL(14,2) NOT NULL,
    STATUS VARCHAR(20) NOT NULL, -- PENDENTE | APROVADO | REJEITADO | CANCELADO
    CRIADO_EM TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Não existe tabela CREDIT_LIMIT: o limite hoje é uma constante no código
-- (CreditLimitService.LIMITE_GLOBAL), não um dado persistido. Qualquer mudança
-- para limite por segmento provavelmente precisa de uma tabela nova, do tipo:
--
-- CREATE TABLE SEGMENT_CREDIT_LIMIT (
--     SEGMENTO VARCHAR(20) PRIMARY KEY,
--     LIMITE DECIMAL(14,2) NOT NULL
-- );
--
-- (comentário deixado por um dev em 2021, nunca implementado)
