package ai.diffy.analysis;

import javax.persistence.*;
import java.util.List;

@Entity
@Table(name = "difference_result")
public class DifferenceResult {
    @Id
    public String id;

    public String traceId;
    public String endpoint;

    @Column
    public Long timestampMsec;

    @OneToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER)
    @JoinColumn(name = "difference_result_id")
    public List<FieldDifference> differences;

    @Column(columnDefinition = "TEXT")
    public String request;

    @Embedded
    public Responses responses;

    public DifferenceResult() {}

    public DifferenceResult(String id, String traceId, String endpoint, Long timestampMsec, List<FieldDifference> differences, String request, Responses responses) {
        this.id = id;
        this.traceId = traceId;
        this.endpoint = endpoint;
        this.timestampMsec = timestampMsec;
        this.differences = differences;
        this.request = request;
        this.responses = responses;
    }
}

