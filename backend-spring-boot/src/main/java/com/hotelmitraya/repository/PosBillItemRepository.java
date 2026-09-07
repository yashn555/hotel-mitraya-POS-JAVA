package com.hotelmitraya.repository;

import com.hotelmitraya.model.PosBillItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PosBillItemRepository extends JpaRepository<PosBillItem, Long> {

    @Query("SELECT i.itemName, SUM(i.quantity), SUM(i.totalPrice) " +
           "FROM PosBillItem i JOIN i.posBill b " +
           "WHERE b.status = 'COMPLETED' " +
           "GROUP BY i.itemName " +
           "ORDER BY SUM(i.quantity) DESC")
    List<Object[]> findBestSellingItems();
}
