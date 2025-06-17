package ai.diffy.analysis;

import javax.persistence.*;

@Entity
@Table(name = "field_difference")
public class FieldDifference {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Long id;

    public String field;

    @Column(columnDefinition = "TEXT")
    public String difference;

    public FieldDifference() {}

    public FieldDifference(String field, String difference) {
        this.field = field;
        this.difference = difference;
    }
}