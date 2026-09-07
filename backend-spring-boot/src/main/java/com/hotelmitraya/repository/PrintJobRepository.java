package com.hotelmitraya.repository;

import com.hotelmitraya.model.PrintJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PrintJobRepository extends JpaRepository<PrintJob, Long> {
    List<PrintJob> findAllByOrderByIdDesc();
    List<PrintJob> findByStatusOrderByIdAsc(String status);
    long countByStatus(String status);
}
