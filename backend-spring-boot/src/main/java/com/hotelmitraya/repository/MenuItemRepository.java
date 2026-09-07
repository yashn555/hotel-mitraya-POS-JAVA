package com.hotelmitraya.repository;

import com.hotelmitraya.model.MenuItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MenuItemRepository extends JpaRepository<MenuItem, Long> {
    List<MenuItem> findByCategoryIdOrderByDisplayOrderAscNameAsc(Long categoryId);
    List<MenuItem> findByCategoryIdAndIsAvailableTrueOrderByDisplayOrderAscNameAsc(Long categoryId);
    List<MenuItem> findByCategoryIsNullAndIsAvailableTrueOrderByDisplayOrderAscNameAsc();
    List<MenuItem> findAllByOrderByDisplayOrderAscNameAsc();
}
