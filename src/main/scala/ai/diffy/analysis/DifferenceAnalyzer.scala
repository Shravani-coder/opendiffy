package ai.diffy.analysis

import ai.diffy.compare.{Difference, NoDifference, PrimitiveDifference}
import ai.diffy.flat.{FlatEntry, FlatObject}
import ai.diffy.lifter.{AnalysisRequest, Message, JsonLifter}
import io.opentelemetry.api.trace.Span
import org.slf4j.LoggerFactory

import java.util.{Date, UUID}
import scala.jdk.CollectionConverters._

object DifferenceAnalyzer {
  val log = LoggerFactory.getLogger(classOf[DifferenceAnalyzer])
  val UndefinedEndpoint = Some("undefined_endpoint")

  def normalizeEndpointName(name: String): String =
    name.replace("/", "-")


//Determining Which Endpoint to Use
  def getEndpointName(
    reqEp: Option[String],
    candEp: Option[String],
    primEp: Option[String],
    secEp: Option[String]
  ): Option[String] = {
    val raw = (reqEp, candEp, primEp, secEp) match {
      case (Some(_), _, _, _)                 => reqEp
      case (_, None, None, None)              => UndefinedEndpoint
      case (_, None, _, _) if primEp == secEp => primEp
      case (_, None, _, _)                    => None
      case (_, Some(_), _, _)                 => candEp
    }
    raw.map(normalizeEndpointName)
  }
}

class DifferenceAnalyzer(
    rawCounter:   RawDifferenceCounter,
    noiseCounter: NoiseDifferenceCounter,
    store:        InMemoryDifferenceCollector
) {
  import DifferenceAnalyzer._

  def analyze(ar: AnalysisRequest): Option[DifferenceResult] =
    apply(ar.request, ar.candidate, ar.primary, ar.secondary)

  def apply(
    request:   Message,
    candidate: Message,
    primary:   Message,
    secondary: Message,
    idKnown:   Option[String] = None
  ): Option[DifferenceResult] = {
    val runIdOpt = request.result.value.get("run_id").collect { case s: String => s }

    // Use a standalone UUID as document ID to keep it short
    val uuid = UUID.randomUUID().toString

    log.info(s"Starting analysis for docId=$uuid runId=${runIdOpt.getOrElse("N/A")}")

    getEndpointName(request.endpoint, candidate.endpoint, primary.endpoint, secondary.endpoint)
      .flatMap { endpointName =>
        log.info(s"Endpoint: $endpointName")

        val requestDiff = FlatObject
          .lift(request.result)
          .rendered
          .map { case FlatEntry(k, v) => s"request.$k.NoDifference" -> NoDifference(v) }
          .toMap

        val rawDiff = requestDiff ++
          Difference(primary.result, candidate.result).flattened.map { case (k, v) => s"response.$k" -> v }

        val noiseDiff = requestDiff ++
          Difference(primary.result, secondary.result).flattened.map { case (k, v) => s"response.$k" -> v }

        log.info(s"Raw diffs: ${rawDiff.size} fields")
        rawDiff.keys.foreach(k => log.debug(s"   ↪ $k"))

        rawCounter.counter.count(endpointName, rawDiff)
        noiseCounter.counter.count(endpointName, noiseDiff ++ requestDiff)

        if (rawDiff.nonEmpty) {
          val dr = new DifferenceResult(
            uuid,                              // short UUID
            runIdOpt.getOrElse(uuid),          // runId field unchanged
            Span.current().getSpanContext.getTraceId,
            endpointName,
            new Date().getTime,
            differencesToJson(rawDiff).asJava,
            JsonLifter.encode(request.result),
            new Responses(
              JsonLifter.encode(primary.result),
              JsonLifter.encode(secondary.result),
              JsonLifter.encode(candidate.result)
            )
          )
          log.info(s"DifferenceResult created for runId=${dr.runId}, endpoint=$endpointName, fields=${dr.differences.size}")
          store.create(dr)
          Some(dr)
        } else {
          log.warn(s" No diffs found for endpoint=$endpointName, docId=$uuid")
          None
        }
      }
  }


//Converts Scala Difference objects into FieldDifference JSON.
  def differencesToJson(diffs: Map[String, Difference]) =
    diffs.toSeq.map {
      case (field, pd: PrimitiveDifference[_]) =>
        new FieldDifference(
          field,
          JsonLifter.encode(pd.toMap.view.mapValues(_.toString).toMap)
        )
      case (field, diff) =>
        new FieldDifference(field, JsonLifter.encode(diff.toMap))
    }
}
