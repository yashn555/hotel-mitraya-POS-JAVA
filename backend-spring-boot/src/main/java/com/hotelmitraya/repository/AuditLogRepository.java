package com.hotelmitraya.repository;

import com.hotelmitraya.model.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    List<AuditLog> findAllByOrderByIdDesc();

    @Query("SELECT a FROM AuditLog a WHERE " +
           "(:action IS NULL OR LOWER(a.action) LIKE LOWER(CONCAT('%', :action, '%'))) AND " +
           "(:entity IS NULL OR UPPER(a.entity) = UPPER(:entity)) " +
           "ORDER BY a.id DESC")
    List<AuditLog> searchAuditLogs(@Param("action") String action, @Param("entity") String entity);
}
