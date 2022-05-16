"""Flask application entrypoint"""

import logging
import os
import time
from flask import Flask, Response, json
import redis

from lib import args, HealthProbes

app = Flask(__name__)

LISTEN_HOST = args.host
LISTEN_PORT = args.port
REDIS_HOST = args.redis_host
REDIS_PORT = args.redis_port

REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
HEALTH_PROBES = HealthProbes(liveness_delay=0, readiness_pass=True)

@app.route('/')
def root():
    """
    Return application cofiguration details.
    This information is useful for this demo application, but it is a terrible
    idea to return data like this in any real application.
    """
    data = json.dumps({
        "appName": "cloud-native-demo",
        "version": "1.0.0",
        "redis-host": REDIS_HOST,
        "env": {
            "host": os.getenv('HOSTNAME'),
            "user_defined_1": os.getenv('USER_DEFINED_1'),
            "user_defined_2": os.getenv('USER_DEFINED_2'),
            "user_defined_3": os.getenv('USER_DEFINED_3')
        }
    })
    return Response(data, mimetype="application/json")


@app.route('/counter')
def counter():
    """
    Returns the value of an incrementing counter for the host where this
    application is running
    """
    hostname = os.getenv("HOSTNAME")

    try:
        if REDIS_CLIENT.hexists("hosts", hostname):
            REDIS_CLIENT.hincrby("hosts", hostname, amount=1)
        else:
            REDIS_CLIENT.hset("hosts", hostname, 1)

        return Response(
            json.dumps(REDIS_CLIENT.hgetall("hosts")),
            status=200,
            mimetype="application/json")
    except redis.exceptions.RedisError:
        return Response(
            json.dumps({"error": "service unavailable"}),
            status=503,
            mimetype="application/json")


@app.route('/counter/reset')
def clear_counter():
    """Clears all counters for all hosts"""
    hosts = REDIS_CLIENT.hgetall("hosts")
    for key in hosts.keys():
        REDIS_CLIENT.hdel("hosts", key)
    return Response(
        json.dumps(REDIS_CLIENT.hgetall("hosts")),
        status=200,
        mimetype="application/json")


@app.route('/live', methods=['GET'])
def live_get():
    """Liveness endpoint to determine whether the application is running"""
    time.sleep(HEALTH_PROBES.liveness_delay)
    return Response(
        json.dumps({"delay": HEALTH_PROBES.liveness_delay}),
        status=200,
        mimetype="application/json")


@app.route('/live/<int:delay>', methods=['GET'])
def live_post(delay):
    """
    Update the simulated delay on the liveness endpoint.
    DEMO NOTE: This would normally be a PUT operation when following REST verb
    semantics.  For the purposes of the demo it will remain a GET to allow easy
    `curl` commands from the CLI.
    e.g. `curl localhost:5000/live/5`
    """
    HEALTH_PROBES.liveness_delay = delay
    return Response(
        json.dumps({"delay": HEALTH_PROBES.liveness_delay}),
        status=200,
        mimetype="application/json")


@app.route('/ready')
def ready():
    """
    Readiness endpoint which will fail if the application is unable to connect
    to its backing Redis dependency.
    """
    redis_ready = False

    try:
        redis_ready = REDIS_CLIENT.ping()
    except redis.exceptions.RedisError as error:
        logging.warning(error)

    response = Response(mimetype="application/json")

    if not HEALTH_PROBES.readiness_pass:
        response.status = "503"
        response.data = json.dumps({
            "reason": "forced readiness failure"
        })
    if redis_ready:
        response.status = "200"
        response.data = json.dumps({
            "redis_connection": "up"
        })
    else:
        response.status = "503"
        response.data = json.dumps({
            "redis_connection": "down"
        })

    return response


@app.route('/ready/fail')
def ready_fail():
    """Allows the readiness check to fail regardless of any other condition"""
    HEALTH_PROBES.readiness_pass = False


if __name__ == '__main__':
    app.run(host=LISTEN_HOST, port=LISTEN_PORT)
