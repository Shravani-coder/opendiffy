

// package ai.diffy;

// import com.samskivert.mustache.DefaultCollector;
// import com.samskivert.mustache.Mustache;
// import org.springframework.boot.SpringApplication;
// import org.springframework.boot.autoconfigure.SpringBootApplication;
// import org.springframework.context.annotation.Bean;

// @SpringBootApplication(
//   scanBasePackages = {
//     "ai.diffy"   // existing code
  
//   }
// )
// public class Main {
//   public static void main(String[] args) {
//     SpringApplication.run(Main.class, args);
//   }

//   @Bean
//   public Mustache.Compiler mustacheCompiler(Mustache.TemplateLoader templateLoader) {
//     return Mustache.compiler()
//                    .defaultValue("Some Default Value")
//                    .withLoader(templateLoader)
//                    .withCollector(new DefaultCollector());
//   }
// }


package ai.diffy;
import com.samskivert.mustache.DefaultCollector;
import com.samskivert.mustache.Mustache;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication(
  scanBasePackages = {
    "ai.diffy"    // keep your own code…
    // …and now also your Java controllers + repos
  }
)
public class Main {
  public static void main(String[] args) {
    SpringApplication.run(Main.class, args);
  }

  @Bean
  public Mustache.Compiler mustacheCompiler(Mustache.TemplateLoader templateLoader) {
    return Mustache.compiler()
                   .defaultValue("Some Default Value")
                   .withLoader(templateLoader)
                   .withCollector(new DefaultCollector());
  }
}




// This Main class is your Spring Boot launcher. When you run it, Spring will:

// Scan ai.diffy packages for components.

// Start up an embedded web server and wire up all your controllers and repositories.

// Provide a ready‑to‑use Mustache compiler bean for rendering any HTML/text templates in your app.