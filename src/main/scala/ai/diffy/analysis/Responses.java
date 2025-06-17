package ai.diffy.analysis;

import javax.persistence.Embeddable;

@Embeddable
public class Responses {
    public String primary;
    public String secondary;
    public String candidate;

    public Responses() {}

    public Responses(String primary, String secondary, String candidate) {
        this.primary = primary;
        this.secondary = secondary;
        this.candidate = candidate;
    }
}