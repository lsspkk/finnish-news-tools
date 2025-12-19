import azure.functions as func
import json
import os
import logging
from datetime import datetime, timezone, timedelta
try:
    from ..shared.app import app
    from ..shared.token_validator import validate_request
except ImportError:
    from shared.app import app
    from shared.token_validator import validate_request

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None

logger = logging.getLogger(__name__)


def _first_day_of_current_month(now: datetime, start_day: int) -> datetime:
    first_day = now.replace(day=start_day, hour=0, minute=0, second=0, microsecond=0)
    if first_day > now:
        if now.month == 1:
            first_day = now.replace(year=now.year - 1, month=12, day=start_day, hour=0, minute=0, second=0, microsecond=0)
        else:
            first_day = now.replace(month=now.month - 1, day=start_day, hour=0, minute=0, second=0, microsecond=0)
    return first_day


def _first_day_of_next_month(now: datetime, start_day: int) -> datetime:
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=start_day, hour=0, minute=0, second=0, microsecond=0)
    else:
        return now.replace(month=now.month + 1, day=start_day, hour=0, minute=0, second=0, microsecond=0)


def _get_total_characters(resource_id: str, billing_start: datetime, billing_end: datetime) -> int:
    if not DefaultAzureCredential:
        logger.error("Azure Monitor dependencies not available")
        raise ImportError("azure-identity package required")
    
    credential = DefaultAzureCredential()
    
    try:
        from azure.monitor.querymetrics import MetricsClient, MetricAggregationType
        region = "westeurope"
        endpoint = f"https://{region}.metrics.monitor.azure.com"
        metrics_client = MetricsClient(endpoint, credential)
        
        # Use tuple form (start_datetime, end_datetime) for timespan
        timespan = (billing_start, billing_end)
        # Use 1 hour granularity for monthly queries
        granularity = timedelta(hours=1)
        
        # query_resources is the correct method for azure-monitor-querymetrics
        response_list = metrics_client.query_resources(
            resource_ids=[resource_id],
            metric_namespace="Microsoft.CognitiveServices/accounts",
            metric_names=["TextCharactersTranslated"],
            timespan=timespan,
            granularity=granularity,
            aggregations=[MetricAggregationType.TOTAL]
        )
        # query_resources returns a list, get first result
        response = response_list[0] if isinstance(response_list, list) and len(response_list) > 0 else response_list
    except ImportError:
        try:
            from azure.monitor.query import MetricsQueryClient
            metrics_client = MetricsQueryClient(credential)
            response = metrics_client.query_resource(
                resource_id=resource_id,
                metric_names=["TextCharactersTranslated"],
                start_time=billing_start,
                end_time=billing_end,
                aggregation="Total"
            )
        except ImportError:
            logger.error("Neither azure-monitor-querymetrics nor azure-monitor-query available")
            raise ImportError("azure-monitor-querymetrics or azure-monitor-query package required")
    
    total_chars = 0
    if hasattr(response, 'metrics'):
        for metric in response.metrics:
            if hasattr(metric, 'timeseries'):
                for time_series in metric.timeseries:
                    if hasattr(time_series, 'data'):
                        for point in time_series.data:
                            if hasattr(point, 'total') and point.total is not None:
                                total_chars += int(point.total)
    elif isinstance(response, list) and len(response) > 0:
        result = response[0]
        if hasattr(result, 'metrics'):
            for metric in result.metrics:
                if hasattr(metric, 'timeseries'):
                    for time_series in metric.timeseries:
                        if hasattr(time_series, 'data'):
                            for point in time_series.data:
                                if hasattr(point, 'total') and point.total is not None:
                                    total_chars += int(point.total)
    
    return total_chars


@app.route(route="translator-quota", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def translator_quota(req: func.HttpRequest) -> func.HttpResponse:
    logger.info('Translator Quota function triggered')
    
    is_valid, username_or_error = validate_request(req)
    if not is_valid:
        logger.warning(f"Authentication failed: {username_or_error}")
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    
    resource_id = os.getenv('AZURE_TRANSLATOR_RESOURCE_ID')
    if not resource_id:
        logger.error("AZURE_TRANSLATOR_RESOURCE_ID not configured")
        return func.HttpResponse(
            json.dumps({"error": "Translator resource ID not configured"}),
            status_code=500,
            mimetype="application/json"
        )
    
    quota_limit = int(os.getenv('AZURE_TRANSLATOR_QUOTA_LIMIT', '2000000'))
    billing_start_day = int(os.getenv('AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY', '1'))
    
    now = datetime.now(timezone.utc)
    billing_start = _first_day_of_current_month(now, billing_start_day)
    billing_end = now
    
    try:
        total_chars = _get_total_characters(resource_id, billing_start, billing_end)
    except Exception as e:
        logger.error(f"Error querying translator quota: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to query quota: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
    
    next_reset = _first_day_of_next_month(now, billing_start_day)
    remaining = max(0, quota_limit - total_chars)
    percentage = round((total_chars / quota_limit * 100), 2) if quota_limit > 0 else 0
    
    result = {
        "total_characters_translated": total_chars,
        "quota_limit": quota_limit,
        "remaining_quota": remaining,
        "percentage_used": percentage,
        "billing_period_start": billing_start.isoformat(),
        "billing_period_end": billing_end.isoformat(),
        "next_reset_time": next_reset.isoformat(),
        "next_reset_date": next_reset.isoformat()
    }
    
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json"
    )
