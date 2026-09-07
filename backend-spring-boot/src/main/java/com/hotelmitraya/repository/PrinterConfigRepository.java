package com.hotelmitraya.repository;

import com.hotelmitraya.model.PrinterConfigModel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface PrinterConfigRepository extends JpaRepository<PrinterConfigModel, Long> {
    Optional<PrinterConfigModel> findFirstByIsDefaultTrue();
}
