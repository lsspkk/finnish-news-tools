# DEVOPS
# Shared FunctionApp instance for v2 programming model

from azure.functions import FunctionApp

# Single FunctionApp instance shared by all functions
app = FunctionApp()

