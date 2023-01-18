#!/usr/bin/env python3

# Reference
# https://blog.doit-intl.com/production-scale-iot-best-practices-with-aws-part-1-of-2-966f21f8aa24

import argparse
import configparser
import datetime
import json
import time
from glob import glob
from os.path import join
import random

from awscrt import io, mqtt
from awsiot import mqtt_connection_builder


CLIENT_NAME_PREFIX = 'iot_'
INTERVAL = 5


def on_connection_interrupted(connection, error, **kwargs):
	print(f"Connection interrupted. error: {error}")


def on_connection_resumed(connection, return_code, session_present, **kwargs):
	print(f"Connection resumed. return_code: {return_code} session_present: {session_present}")


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
iot_endpoint = config["SETTINGS"]["IOT_ENDPOINT"]
device_project_name = config["SETTINGS"]["DEVICE_PROJECT_NAME"]
device_function = config["SETTINGS"]["DEVICE_FUNCTION_TYPE"]
device_location = config["SETTINGS"]["DEVICE_LOCATION"]
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

sensor_topic = config["SETTINGS"]["IOT_TOPIC"].replace(r"${iot:Connection.Thing.ThingName}", client_id)
sensor_topic = sensor_topic.replace("${iot:Connection.Thing.Attributes[ProjectName]}", device_project_name)
sensor_topic = sensor_topic.replace("${iot:Connection.Thing.Attributes[FunctionType]}", device_function)

print(f"Connecting to {iot_endpoint} with client ID '{client_id}'...")
connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected!")


temperature = 0

while True:

	### TODO
	### Read Temperature from Sensor 
	################################

	temperature = temperature + random.randint(-1,2)

	################################

	message = {
		"ThingName": client_id,
		"Timestamp": datetime.datetime.now().strftime("%Y-%d-%m %H:%M:%S"),
		"TempC": temperature,
		"ProjectName": device_project_name,
		"Location": device_location,
		"FunctionType": device_function
	}
	print(f"Publishing message to topic '{sensor_topic}': {message}")
	mqtt_connection.publish(
		topic=sensor_topic,
		payload=json.dumps(message),
		qos=mqtt.QoS.AT_LEAST_ONCE)
	time.sleep(INTERVAL)