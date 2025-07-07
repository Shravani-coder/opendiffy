package ai.diffy.lifter

import ai.diffy.Settings
import ai.diffy.proxy.{HttpMessage, HttpRequest, HttpResponse}
import ai.diffy.util.ResourceMatcher
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.stereotype.Component

import scala.collection.JavaConverters._

object HttpLifter {
  val ControllerEndpointHeaderName = "X-Action-Name"
  val RunIdHeaderName = "X-Run-Id"
  val log = LoggerFactory.getLogger("HttpLifter")

  def contentTypeNotSupportedException(contentType: String) =
    new Exception(s"Content type: $contentType is not supported")

  case class MalformedJsonContentException(cause: Throwable)
    extends Exception("Malformed Json content") {
    initCause(cause)
  }
}

class HttpLifter(settings: Settings) {
  import HttpLifter._

  def liftRequest(req: HttpRequest): Message = {
    val headers = req.getHeaders.asScala.toMap
    log.info(s"Lifting request: ${req.getMethod} ${req.getPath}")
    log.debug(s" Headers: $headers")

    val runIdOpt: Option[String] = headers.get(RunIdHeaderName)
    log.info(s"Extracted run_id: ${runIdOpt.getOrElse("N/A")}")

    val canonicalResource: Option[String] =
      headers
        .get("Canonical-Resource")
        .orElse(settings.resourceMatcher.flatMap(_.resourceName(req.getPath)))
        .orElse(Some(s"${req.getMethod}:${req.getPath}"))

    log.info(s"Canonical Resource: ${canonicalResource.getOrElse("undefined")}")

    val params = req.getParams
    val body = try {
      StringLifter.lift(req.getBody)
    } catch {
      case e: Exception =>
        log.error(" Failed to lift request body", e)
        throw MalformedJsonContentException(e)
    }

    val baseMap = Map(
      "method" -> req.getMethod,
      "path" -> req.getPath,
      "uri" -> req.getUri,
      "headers" -> headers,
      "params" -> params,
      "body" -> body
    ) ++ runIdOpt.map("run_id" -> _)

    log.debug(s" Request FieldMap: $baseMap")

    Message(
      canonicalResource,
      new FieldMap(baseMap)
    )
  }

  def liftResponse(r: HttpResponse): Message = {
    log.info(s"Lifting response with status=${r.getStatus}")
    val responseMap = Map(
      "status" -> r.getStatus,
      "body" -> StringLifter.lift(r.getBody())
    ) ++ headersMap(r)

    log.debug(s" Response FieldMap: $responseMap")

    Message(None, new FieldMap(responseMap))
  }

  private[this] def headersMap(response: HttpMessage): Map[String, Any] =
    if (!settings.excludeHttpHeadersComparison)
      Map("headers" -> new FieldMap(response.getHeaders.asScala.toMap))
    else Map.empty
}