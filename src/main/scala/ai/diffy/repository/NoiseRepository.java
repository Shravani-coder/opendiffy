package ai.diffy.repository;

import org.springframework.data.repository.CrudRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface NoiseRepository extends CrudRepository<Noise, String> {
}
