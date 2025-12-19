#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

functions_dir = Path(__file__).parent.parent
sys.path.insert(0, str(functions_dir))
sys.path.insert(0, str(functions_dir.parent))

from shared.token_validator import generate_token
import azure.functions as func


class MockHeaders:
    def __init__(self, headers_dict):
        self._headers = headers_dict
    
    def get(self, key, default=None):
        return self._headers.get(key, default)


class MockParams:
    def __init__(self, params_dict):
        self._params = params_dict
    
    def get(self, key, default=None):
        return self._params.get(key, default)


class MockHttpRequest:
    def __init__(self, method='GET', params=None, body=None, headers=None):
        self.method = method
        self.params = MockParams(params or {})
        self._body = body
        self.headers = MockHeaders(headers or {})
    
    def get(self, key, default=None):
        return self.params.get(key, default)
    
    def get_json(self):
        if isinstance(self._body, dict):
            return self._body
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body
    
    def get_header(self, name):
        return self.headers.get(name)


def authenticate_user(username: str, password: str) -> dict:
    from authenticate import authenticate as authenticate_func
    
    request = MockHttpRequest(
        method='POST',
        body={
            "username": username,
            "password": password
        }
    )
    
    response = authenticate_func(request)
    
    body_bytes = response.get_body()
    if isinstance(body_bytes, bytes):
        body_str = body_bytes.decode('utf-8')
    else:
        body_str = str(body_bytes)
    
    if response.status_code == 200:
        auth_data = json.loads(body_str)
        return {
            "token": auth_data["token"],
            "username": auth_data["username"],
            "issued_date": auth_data["issued_at"]
        }
    else:
        error_data = json.loads(body_str)
        raise ValueError(f"Authentication failed: {error_data.get('error', 'Unknown error')}")


def create_auth_headers(auth_data: dict) -> dict:
    return {
        "X-Token": auth_data["token"],
        "X-Username": auth_data["username"],
        "X-Issued-Date": auth_data["issued_date"]
    }


def test_translator_quota_mocked(auth_headers: dict):
    from translator_quota import translator_quota
    
    mock_metric_point = MagicMock()
    mock_metric_point.total = 1250000
    
    mock_time_series = MagicMock()
    mock_time_series.data = [mock_metric_point]
    
    mock_metric = MagicMock()
    mock_metric.timeseries = [mock_time_series]
    
    mock_response = MagicMock()
    mock_response.metrics = [mock_metric]
    
    request = MockHttpRequest(
        method='GET',
        headers=auth_headers
    )
    
    os.environ['AZURE_TRANSLATOR_RESOURCE_ID'] = '/subscriptions/test/resourceGroups/test/providers/Microsoft.CognitiveServices/accounts/test'
    os.environ['AZURE_TRANSLATOR_QUOTA_LIMIT'] = '2000000'
    os.environ['AZURE_TRANSLATOR_BILLING_CYCLE_START_DAY'] = '1'
    
    with patch('azure.monitor.querymetrics.MetricsClient') as mock_client_class, \
         patch('azure.identity.DefaultAzureCredential'):
        
        mock_client = MagicMock()
        mock_client.query_resources.return_value = [mock_response]
        mock_client_class.return_value = mock_client
        
        response = translator_quota(request)
        
        body_bytes = response.get_body()
        if isinstance(body_bytes, bytes):
            body_str = body_bytes.decode('utf-8')
        else:
            body_str = str(body_bytes)
        
        if response.status_code == 200:
            quota_data = json.loads(body_str)
            print("\n=== Translator Quota (Mocked) ===")
            print(json.dumps(quota_data, indent=2))
            return quota_data
        else:
            error_data = json.loads(body_str)
            print(f"\n=== Error ===")
            print(json.dumps(error_data, indent=2))
            raise ValueError(f"Quota query failed: {error_data.get('error', 'Unknown error')}")


def test_translator_quota_real(auth_headers: dict):
    from translator_quota import translator_quota
    
    resource_id = os.getenv('AZURE_TRANSLATOR_RESOURCE_ID')
    if not resource_id or resource_id.startswith('/subscriptions/{') or '{sub}' in resource_id:
        print("\n=== Skipping real Azure Monitor test ===")
        print("AZURE_TRANSLATOR_RESOURCE_ID not configured or using template value")
        print("Run ./tests/setup-local-monitor-test.sh to configure")
        return None
    
    print(f"\nUsing resource ID: {resource_id}")
    
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token = credential.get_token("https://monitor.azure.com/.default")
        print("✓ Azure credentials verified")
    except Exception as e:
        print(f"\n⚠ Azure credentials error: {e}")
        print("Make sure you're logged in: az login")
        return None
    
    request = MockHttpRequest(
        method='GET',
        headers=auth_headers
    )
    
    response = translator_quota(request)
    
    body_bytes = response.get_body()
    if isinstance(body_bytes, bytes):
        body_str = body_bytes.decode('utf-8')
    else:
        body_str = str(body_bytes)
    
    if response.status_code == 200:
        quota_data = json.loads(body_str)
        print("\n=== Translator Quota (Real Azure Monitor) ===")
        print(json.dumps(quota_data, indent=2))
        return quota_data
    else:
        error_data = json.loads(body_str)
        print(f"\n=== Error ===")
        print(json.dumps(error_data, indent=2))
        print("\nNote: This might be a permissions issue.")
        print("Make sure you have Monitoring Reader role on the Translator resource.")
        raise ValueError(f"Quota query failed: {error_data.get('error', 'Unknown error')}")


def load_local_settings():
    settings_file = Path(__file__).parent.parent / 'local.settings.json.local'
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            settings = json.load(f)
            if 'Values' in settings:
                for key, value in settings['Values'].items():
                    if key not in os.environ:
                        os.environ[key] = str(value)


def main():
    load_local_settings()
    
    os.environ.setdefault('USE_LOCAL_STORAGE', 'true')
    os.environ.setdefault('LOCAL_STORAGE_PATH', './local-dev/storage')
    os.environ.setdefault('LOCAL_TABLES_PATH', './local-dev/tables')
    os.environ.setdefault('STORAGE_CONTAINER', 'finnish-news-tools')
    os.environ.setdefault('RATE_LIMIT_TABLE_NAME', 'rateLimits')
    os.environ.setdefault('AUTH_SECRET', 'test-secret-key-change-in-production')
    
    print("=== Translator Quota Test ===")
    
    username = input("Username: ").strip() or "test_user"
    password = input("Password: ").strip() or "Hello world!"
    
    try:
        auth_data = authenticate_user(username, password)
        print(f"\n✓ Authenticated as {auth_data['username']}")
        
        auth_headers = create_auth_headers(auth_data)
        
        resource_id = os.getenv('AZURE_TRANSLATOR_RESOURCE_ID', '')
        use_real = resource_id and not resource_id.startswith('/subscriptions/{') and '{sub}' not in resource_id and '/test/' not in resource_id
        
        if use_real:
            print("\n--- Testing with real Azure Monitor API ---")
            try:
                test_translator_quota_real(auth_headers)
            except Exception as e:
                print(f"\nReal API test failed: {e}")
                print("Falling back to mocked test...")
                print("\n--- Testing with mocked Azure Monitor API ---")
                test_translator_quota_mocked(auth_headers)
        else:
            print("\n--- Testing with mocked Azure Monitor API ---")
            test_translator_quota_mocked(auth_headers)
            
            if use_real or (resource_id and '/test/' not in resource_id):
                print("\n--- Testing with real Azure Monitor API (if configured) ---")
                try:
                    test_translator_quota_real(auth_headers)
                except Exception as e:
                    print(f"\n⚠ Real API test skipped or failed: {e}")
                    print("This is expected if AZURE_TRANSLATOR_RESOURCE_ID is not properly configured.")
        
        print("\n✓ All tests completed")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
