package ai.diffy.transformations;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;

@Entity
@Table(name = "transformation")
public class Transformation {
    @Id
    public String injectionPoint;
    public String transformationJs;

    public Transformation() {}

    public Transformation(String injectionPoint, String transformationJs) {
        this.injectionPoint = injectionPoint;
        this.transformationJs = transformationJs;
    }

    public String getTransformationJs() {
        return transformationJs;
    }
}
