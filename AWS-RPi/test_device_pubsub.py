#!/usr/bin/env python3

# Reference
# https://blog.doit-intl.com/production-scale-iot-best-practices-with-aws-part-1-of-2-966f21f8aa24

import argparse
import configparser
import json
import random
import sys
from os.path import join
from time import sleep

from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

CLIENT_NAME_PREFIX = 'iot_'

def on_connection_interrupted(connection, error, **kwargs):
	print(f"Connection interrupted. error: {error}")


def on_connection_resumed(connection, return_code, session_present, **kwargs):
	print(f"Connection resumed. return_code: {return_code} session_present: {session_present}")

	if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
		print("Session did not persist. Resubscribing to existing topics...")
		resubscribe_future, _ = connection.resubscribe_existing_topics()
		resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
	resubscribe_results = resubscribe_future.result()
	print(f"Resubscribe results: {resubscribe_results}")

	for resub_topic, qos in resubscribe_results["topics"]:
		if qos is None:
			sys.exit(f"Server rejected resubscribe to topic: {resub_topic}")


def on_message_received(topic, payload, **kwargs):
	payload = payload.decode("UTF-8")
	print(f"Received message from topic '{topic}': {payload}")


# Parse arguments for AWS IoT connection configuration values
parser = argparse.ArgumentParser(description="Connect and register a new device to the AWS IoT platform")
parser.add_argument("-c", "--config",
					type=str,
					default="perm_config.ini",
					metavar="ConnectionConfigFile",
					help="File defining the path where cert files are stored, cert filenames, and an IoT endpoint")
args = parser.parse_args()

# Parse connection configuration values
config = configparser.ConfigParser()
config.read(args.config)
print(args.config)
print({section: dict(config[section]) for section in config.sections()})

iot_endpoint = config["SETTINGS"]["IOT_ENDPOINT"]
device_project_name = config["SETTINGS"]["DEVICE_PROJECT_NAME"]
device_function = config["SETTINGS"]["DEVICE_FUNCTION_TYPE"]
root_cert_path = config["SETTINGS"]["ROOT_CERT"]
private_key_path = config["SETTINGS"]["SECURE_KEY"]
cert_path = config["SETTINGS"]["CLAIM_CERT"]

# Gather the UUID machine-id from your Linux device
with open("/etc/machine-id") as file:
	machine_uuid = file.readline().rstrip()

event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

client_id = f"{CLIENT_NAME_PREFIX}{machine_uuid}"
mqtt_connection = mqtt_connection_builder.mtls_from_path(
	endpoint=iot_endpoint,
	cert_filepath=cert_path,
	pri_key_filepath=private_key_path,
	client_bootstrap=client_bootstrap,
	ca_filepath=root_cert_path,
	client_id=client_id,
	on_connection_interrupted=on_connection_interrupted,
	on_connection_resumed=on_connection_resumed,
	clean_session=False,
	keep_alive_secs=6)

# io.init_logging(io.LogLevel.Info, 'stderr')

sensor_topic = config["SETTINGS"]["IOT_TOPIC"].replace(r"${iot:Connection.Thing.ThingName}", client_id)
sensor_topic = sensor_topic.replace("${iot:Connection.Thing.Attributes[ProjectName]}", device_project_name)
sensor_topic = sensor_topic.replace("${iot:Connection.Thing.Attributes[FunctionType]}", device_function)

print(f"Connecting to {iot_endpoint} with client ID '{client_id}'...")
connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected!")

# Subscribe to the topic to verify that messages are being published
print(f"Subscribing to topic '{sensor_topic}' ...")
subscribe_future, packet_id = mqtt_connection.subscribe(
	topic=sensor_topic,
	qos=mqtt.QoS.AT_LEAST_ONCE,
	callback=on_message_received)

subscribe_result = subscribe_future.result()
print(f"Subscribed with {str(subscribe_result)}")

while True:
	message = {"TempF": str(random.randint(70, 95))}  # Publish random simulated room temperatures in Fahrenheit
	print(f"Publishing message to topic '{sensor_topic}': {message}")
	mqtt_connection.publish(
		topic=sensor_topic,
		payload=json.dumps(message),
		qos=mqtt.QoS.AT_LEAST_ONCE)
	sleep(1)