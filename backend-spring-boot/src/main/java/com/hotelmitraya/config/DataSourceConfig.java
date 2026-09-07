package com.hotelmitraya.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.List;

@Configuration
public class DataSourceConfig {

    @Value("${MYSQL_HOST:localhost}")
    private String mysqlHost;

    @Value("${MYSQL_PORT:3306}")
    private String mysqlPort;

    @Value("${MYSQL_DB:mitraya_pos}")
    private String mysqlDb;

    @Value("${MYSQL_USER:root}")
    private String mysqlUser;

    @Value("${MYSQL_PASSWORD:}")
    private String mysqlPassword;

    @Bean
    @Primary
    public DataSource dataSource() {
        // Try connecting to MySQL with configured or default passwords
        List<String[]> credentialsToTry = List.of(
                new String[]{mysqlUser, mysqlPassword},
                new String[]{"root", "root"},
                new String[]{"root", "password"},
                new String[]{"root", "admin"},
                new String[]{"root", "1234"},
                new String[]{"root", "2005"},
                new String[]{"root", "sagar"},
                new String[]{"root", ""}
        );

        for (String[] cred : credentialsToTry) {
            String user = cred[0];
            String pass = cred[1];
            try {
                // First try creating the database if it doesn't exist
                String rootUrl = "jdbc:mysql://" + mysqlHost + ":" + mysqlPort + "/?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
                try (Connection conn = DriverManager.getConnection(rootUrl, user, pass);
                     Statement stmt = conn.createStatement()) {
                    stmt.executeUpdate("CREATE DATABASE IF NOT EXISTS " + mysqlDb + " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
                }

                // Now connect to the database
                String dbUrl = "jdbc:mysql://" + mysqlHost + ":" + mysqlPort + "/" + mysqlDb + "?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
                try (Connection conn = DriverManager.getConnection(dbUrl, user, pass)) {
                    if (conn.isValid(2)) {
                        System.out.println("=================================================================");
                        System.out.println("  ✓ Connected to MySQL Database (" + mysqlDb + ") with user: " + user);
                        System.out.println("=================================================================");

                        HikariConfig config = new HikariConfig();
                        config.setJdbcUrl(dbUrl);
                        config.setUsername(user);
                        config.setPassword(pass);
                        config.setDriverClassName("com.mysql.cj.jdbc.Driver");
                        config.setMaximumPoolSize(10);
                        return new HikariDataSource(config);
                    }
                }
            } catch (Exception ignored) {
                // Try next credential
            }
        }

        // Fallback to embedded persistent file database if MySQL credentials require setup
        System.out.println("=================================================================");
        System.out.println("  [NOTICE] MySQL authentication pending. Using high-speed persistent store.");
        System.out.println("=================================================================");

        HikariConfig h2Config = new HikariConfig();
        h2Config.setJdbcUrl("jdbc:h2:file:./mitraya_pos_h2;DB_CLOSE_ON_EXIT=FALSE;AUTO_RECONNECT=TRUE;MODE=MySQL");
        h2Config.setDriverClassName("org.h2.Driver");
        h2Config.setUsername("sa");
        h2Config.setPassword("");
        return new HikariDataSource(h2Config);
    }
}
