package ai.diffy.analysis;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.List;

@Document
public class DifferenceResult {
    @Id
    public final String id;

    @Indexed
    public String runId;           // <— new

    public String traceId;
    public String endpoint;

    @Indexed
    public Long timestampMsec;

    public List<FieldDifference> differences;
    public String request;
    public Responses responses;

    public DifferenceResult(
        String id,
        String runId,                      // <— new
        String traceId,
        String endpoint,
        Long timestampMsec,
        List<FieldDifference> differences,
        String request,
        Responses responses
    ) {
        this.id           = id;
        this.runId        = runId;      // <— new
        this.traceId      = traceId;
        this.endpoint     = endpoint;
        this.timestampMsec= timestampMsec;
        this.differences  = differences;
        this.request      = request;
        this.responses    = responses;
    }
}
