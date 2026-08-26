package br.com.legado.financeiro;

import java.math.BigDecimal;
import java.sql.*;

/**
 * Acesso direto a tabela CUSTOMER via JDBC puro (sem ORM).
 * Legado: reescrever com Hibernate um dia (issue aberta desde 2015).
 */
public class CustomerRepository {

    private Connection connection;

    public CustomerRepository(Connection connection) {
        this.connection = connection;
    }

    /**
     * Busca cliente pelo id.
     * A coluna SEGMENTO existe na tabela desde a migracao de 2019,
     * mas quase nenhum servico do sistema usa esse campo ainda.
     */
    public Customer findById(String customerId) {
        String sql = "SELECT ID, NOME, SEGMENTO, EMAIL FROM CUSTOMER WHERE ID = ?";
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.setString(1, customerId);
            ResultSet rs = stmt.executeQuery();
            if (!rs.next()) {
                return null;
            }
            Customer customer = new Customer();
            customer.setId(rs.getString("ID"));
            customer.setNome(rs.getString("NOME"));
            customer.setSegmento(rs.getString("SEGMENTO"));
            customer.setEmail(rs.getString("EMAIL"));
            return customer;
        } catch (SQLException e) {
            throw new RuntimeException("Falha ao buscar cliente", e);
        }
    }

    /**
     * Soma o valor de pedidos em aberto do cliente.
     * Consulta feita direto na tabela ORDER_ITEM, sem cache.
     */
    public BigDecimal getTotalUtilizado(String customerId) {
        String sql = "SELECT COALESCE(SUM(VALOR_TOTAL), 0) FROM CUSTOMER_ORDER "
                + "WHERE CUSTOMER_ID = ? AND STATUS IN ('PENDENTE', 'APROVADO')";
        try (PreparedStatement stmt = connection.prepareStatement(sql)) {
            stmt.setString(1, customerId);
            ResultSet rs = stmt.executeQuery();
            rs.next();
            return rs.getBigDecimal(1);
        } catch (SQLException e) {
            throw new RuntimeException("Falha ao calcular total utilizado", e);
        }
    }
}
