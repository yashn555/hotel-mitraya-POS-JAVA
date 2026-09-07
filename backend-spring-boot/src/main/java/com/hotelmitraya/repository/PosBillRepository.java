package com.hotelmitraya.repository;

import com.hotelmitraya.model.PosBill;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface PosBillRepository extends JpaRepository<PosBill, Long> {
    Optional<PosBill> findByBillNumber(String billNumber);

    Optional<PosBill> findFirstByOrderByIdDesc();

    List<PosBill> findByStatusOrderByIdDesc(String status);

    List<PosBill> findByCreatedAtBetweenAndStatus(LocalDateTime start, LocalDateTime end, String status);

    long countByStatus(String status);

    @Query("SELECT COALESCE(SUM(b.totalAmount), 0.0) FROM PosBill b WHERE b.status = :status")
    Double sumTotalAmountByStatus(@Param("status") String status);

    @Query("SELECT b FROM PosBill b WHERE " +
           "(:status IS NULL OR b.status = :status) AND " +
           "(:searchQuery IS NULL OR LOWER(b.billNumber) LIKE LOWER(CONCAT('%', :searchQuery, '%')) OR LOWER(b.customerName) LIKE LOWER(CONCAT('%', :searchQuery, '%'))) AND " +
           "(:paymentMode IS NULL OR b.paymentMode = :paymentMode) AND " +
           "(:startDate IS NULL OR b.createdAt >= :startDate) AND " +
           "(:endDate IS NULL OR b.createdAt <= :endDate) " +
           "ORDER BY b.id DESC")
    List<PosBill> searchBills(
            @Param("status") String status,
            @Param("searchQuery") String searchQuery,
            @Param("paymentMode") String paymentMode,
            @Param("startDate") LocalDateTime startDate,
            @Param("endDate") LocalDateTime endDate
    );
}
