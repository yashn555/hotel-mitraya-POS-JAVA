package com.hotelmitraya.repository;

import com.hotelmitraya.model.PrintEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PrintEventRepository extends JpaRepository<PrintEvent, Long> {
    @Query("SELECT COALESCE(MAX(e.id), 0) FROM PrintEvent e")
    Long findMaxId();

    List<PrintEvent> findByIdGreaterThanOrderByIdAsc(Long sinceId);
}
