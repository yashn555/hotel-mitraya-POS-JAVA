package com.hotelmitraya.repository;

import com.hotelmitraya.model.Order;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    Optional<Order> findByOrderNumber(String orderNumber);

    List<Order> findByStatusInOrderByIdAsc(Collection<String> statuses);

    List<Order> findByOrderTypeAndStatusIn(String orderType, Collection<String> statuses);

    Optional<Order> findFirstByTableNumberAndOrderTypeAndStatusIn(Integer tableNumber, String orderType, Collection<String> statuses);

    Optional<Order> findFirstByOrderNumberStartingWithOrderByIdDesc(String prefix);

    @Query("SELECT o FROM Order o WHERE " +
           "(:userId IS NULL OR o.createdByUserId = :userId) AND " +
           "(:statuses IS NULL OR o.status IN :statuses) AND " +
           "(:tableNumber IS NULL OR o.tableNumber = :tableNumber) " +
           "ORDER BY o.id DESC")
    List<Order> findOrdersWithFilters(
            @Param("userId") Long userId,
            @Param("statuses") Collection<String> statuses,
            @Param("tableNumber") Integer tableNumber
    );
}
