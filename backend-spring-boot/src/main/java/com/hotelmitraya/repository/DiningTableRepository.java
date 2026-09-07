package com.hotelmitraya.repository;

import com.hotelmitraya.model.DiningTable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DiningTableRepository extends JpaRepository<DiningTable, Long> {
    Optional<DiningTable> findByTableNumber(Integer tableNumber);
    List<DiningTable> findAllByOrderByTableNumberAsc();
}
