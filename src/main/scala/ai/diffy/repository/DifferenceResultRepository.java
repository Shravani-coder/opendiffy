package ai.diffy.repository;

import ai.diffy.analysis.DifferenceResult;
import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DifferenceResultRepository extends CrudRepository<DifferenceResult, String> {
    List<DifferenceResult> findByTimestampMsecBetween(Long start, Long end);
}
