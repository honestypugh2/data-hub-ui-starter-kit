"""Azure Functions v2 entry point — registers all HTTP-triggered blueprints."""

import azure.functions as func

from upload_initiate import bp as upload_bp
from get_status import bp as status_bp
from get_results import bp as results_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(upload_bp)
app.register_functions(status_bp)
app.register_functions(results_bp)
