import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.data.tables import TableServiceClient
from .local_storage import LocalBlobStorage, LocalTableStorage

logger = logging.getLogger(__name__)


def get_blob_storage():
    use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
    
    if use_local:
        base_path = os.getenv('LOCAL_STORAGE_PATH', './local-dev/storage')
        logger.info(f"Using LocalBlobStorage at {base_path}")
        return LocalBlobStorage(base_path)
    else:
        # Azure Functions uses AzureWebJobsStorage, but we also check AZURE_STORAGE_CONNECTION_STRING
        connection_string = os.getenv('AzureWebJobsStorage') or os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("AzureWebJobsStorage or AZURE_STORAGE_CONNECTION_STRING not set")
        logger.info("Using Azure Blob Storage")
        return BlobServiceClient.from_connection_string(connection_string)


def get_table_storage(table_name: str):
    use_local = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
    
    if use_local:
        tables_path = os.getenv('LOCAL_TABLES_PATH', './local-dev/tables')
        table_file = f"{tables_path}/{table_name}.json"
        logger.info(f"Using LocalTableStorage at {table_file}")
        return LocalTableStorage(table_file)
    else:
        # Azure Functions uses AzureWebJobsStorage, but we prefer AZURE_STORAGE_TABLE_CONNECTION_STRING if set
        connection_string = os.getenv('AZURE_STORAGE_TABLE_CONNECTION_STRING') or os.getenv('AzureWebJobsStorage')
        if not connection_string:
            raise ValueError("AZURE_STORAGE_TABLE_CONNECTION_STRING or AzureWebJobsStorage not set")
        logger.info(f"Using Azure Table Storage: {table_name}")
        table_service = TableServiceClient.from_connection_string(connection_string)
        return table_service.get_table_client(table_name)
