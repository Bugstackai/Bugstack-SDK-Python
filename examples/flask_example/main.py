"""Flask example with BugStack error capture."""

from flask import Flask

import bugstack
from bugstack.integrations.flask import init_app

bugstack.init(
    api_key="bs_live_your_api_key_here",
    auto_fix=True,
)

app = Flask(__name__)
init_app(app)


@app.route("/")
def index():
    return "Hello, World!"


@app.route("/fail")
def fail():
    raise RuntimeError("Something went wrong!")


# Run: flask run
if __name__ == "__main__":
    app.run(debug=True)
