package ai.diffy.repository;

import javax.persistence.ElementCollection;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.List;

@Entity
@Table(name = "noise")
public class Noise {
    @Id
    public String endpoint;

    @ElementCollection
    public List<String> noisyfields;

    public Noise() {}

    public Noise(String endpoint, List<String> noisyfields) {
        this.endpoint = endpoint;
        this.noisyfields = noisyfields;
    }
}
