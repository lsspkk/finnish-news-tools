#!/usr/bin/env python3
"""
DEVOPS
Check Azure Function App Logs
Fetches recent logs from Azure Function App using Azure CLI
"""

import subprocess
import sys
import os
from pathlib import Path

def load_resource_names():
    """Load resource names from resource-names.env"""
    script_dir = Path(__file__).parent.parent
    env_file = script_dir / "resource-names.env"
    
    if not env_file.exists():
        print(f"Error: {env_file} not found")
        print("Create it by copying: cp resource-names.env.template resource-names.env")
        sys.exit(1)
    
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

def get_logs(function_app_name, resource_group, lines=100, follow=False):
    """Get logs from Azure Function App"""
    if follow:
        # For live streaming, use log stream
        cmd = [
            "az", "webapp", "log", "tail",
            "--name", function_app_name,
            "--resource-group", resource_group
        ]
        print(f"Streaming logs from Function App: {function_app_name}")
        print("Press Ctrl+C to stop")
        print("")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                print(line, end='')
        except KeyboardInterrupt:
            process.terminate()
            print("\nStopped streaming logs")
    else:
        # Try to get logs via Kudu API or Application Insights
        print(f"Fetching recent logs from Function App: {function_app_name}")
        print("")
        print("Note: For detailed logs, use Azure Portal:")
        print(f"  https://portal.azure.com -> Function App -> {function_app_name} -> Log stream")
        print("")
        print("Or use Application Insights if configured:")
        print(f"  https://portal.azure.com -> Application Insights -> {function_app_name}")
        print("")
        
        # Try to get recent invocation logs via Kudu API
        try:
            # Get function app URL
            cmd = [
                "az", "functionapp", "show",
                "--name", function_app_name,
                "--resource-group", resource_group,
                "--query", "defaultHostName",
                "--output", "tsv"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            hostname = result.stdout.strip()
            
            if hostname:
                print(f"Function App URL: https://{hostname}")
                print("")
                print("To view logs in real-time, run:")
                print(f"  {sys.argv[0]} --follow")
                print("")
                print("Or check recent invocations in Azure Portal:")
                print(f"  https://portal.azure.com -> Function App -> {function_app_name} -> Functions -> rss-feed-parser -> Monitor")
        except Exception as e:
            print(f"Could not fetch log details: {e}")
            print("Check Azure Portal for logs")

def main():
    resource_names = load_resource_names()
    
    function_app_name = resource_names.get('FUNCTION_APP_NAME')
    resource_group = resource_names.get('RESOURCE_GROUP')
    
    if not function_app_name or not resource_group:
        print("Error: FUNCTION_APP_NAME and RESOURCE_GROUP must be set in resource-names.env")
        sys.exit(1)
    
    # Parse command line arguments
    lines = 100
    follow = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--follow' or sys.argv[1] == '-f':
            follow = True
        else:
            try:
                lines = int(sys.argv[1])
            except ValueError:
                print(f"Usage: {sys.argv[0]} [lines|--follow]")
                sys.exit(1)
    
    if len(sys.argv) > 2 and (sys.argv[2] == '--follow' or sys.argv[2] == '-f'):
        follow = True
    
    get_logs(function_app_name, resource_group, lines, follow)
    
    if not follow:
        print("")
        print(f"Tip: Use '{sys.argv[0]} --follow' for live streaming")
        print(f"Or check logs in Azure Portal: https://portal.azure.com")

if __name__ == "__main__":
    main()

