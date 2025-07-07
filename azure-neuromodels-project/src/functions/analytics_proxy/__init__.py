import azure.functions as func
import json
from .main import main

def handler(req: func.HttpRequest) -> func.HttpResponse:
    return main(req)
