#!/usr/bin/env python3

# Reference
# https://blog.doit-intl.com/production-scale-iot-best-practices-with-aws-part-1-of-2-966f21f8aa24

import argparse
import configparser
import json
import shutil
import sys
from os import makedirs
from os.path import join
from time import sleep

from awscrt import io, mqtt
from awsiot import iotidentity, mqtt_connection_builder

create_keys_and_certificate_response = None
register_thing_response = None



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
	for resub_topic, qos in resubscribe_results['topics']:
		if qos is None:
			sys.exit(f"Server rejected resubscribe to topic: {resub_topic}")


def createkeysandcertificate_execution_accepted(response):
	try:
		global create_keys_and_certificate_response
		create_keys_and_certificate_response = response
		print(f"Received a new message: {create_keys_and_certificate_response}")
		return
	except Exception as e:
		sys.exit(e)


def createkeysandcertificate_execution_rejected(rejected):
	sys.exit(f"CreateKeysAndCertificate Request rejected with code:'{rejected.error_code}' message:'{rejected.error_message}' statuscode:'{rejected.status_code}'")


def on_publish_create_keys_and_certificate(future):
	try:
		future.result()  # Raises exception if publish failed
		print("Published CreateKeysAndCertificate request..")
	except Exception as e:
		print("Failed to publish CreateKeysAndCertificate request.")
		sys.exit(e)


def registerthing_execution_accepted(response):
	try:
		global register_thing_response
		register_thing_response = response
		print(f"Received a new message {register_thing_response} ")
		return
	except Exception as e:
		sys.exit(e)


def registerthing_execution_rejected(rejected):
	sys.exit(f"RegisterThing Request rejected with code:'{rejected.error_code}' message:'{rejected.error_message}' statuscode:'{rejected.status_code}'")


def wait_for_create_keys_and_certificate_response():
	loop_count = 0
	while loop_count < 10 and create_keys_and_certificate_response is None:
		if create_keys_and_certificate_response is not None:
			break
		print(f"Waiting... CreateKeysAndCertificateResponse: {json.dumps(create_keys_and_certificate_response)}")
		loop_count += 1
		sleep(1)


def on_publish_register_thing(future):
	try:
		future.result()  # Raises exception if publish failed
		print("Published RegisterThing request..")
	except Exception as e:
		print("Failed to publish RegisterThing request.")
		sys.exit(e)


def wait_for_register_thing_response():
	loop_count = 0
	while loop_count < 10 and register_thing_response is None:
		if register_thing_response is not None:
			break
		loop_count += 1
		print(f"Waiting... RegisterThingResponse: {json.dumps(register_thing_response)}")
		sleep(1)


# Parse arguments for AWS IoT connection configuration values
parser = argparse.ArgumentParser(description="Connect and register a new device to the AWS IoT platform")
parser.add_argument('-c', '--config',
					type=str,
					default="config.ini",
					metavar="ConnectionConfigFile",
					help="File defining the path where cert files are stored, cert filenames, an IoT endpoint, and the fleet provisioning template name")
parser.add_argument('-p', '--project',
					type=str,
					required=True,
					metavar="ProjectName",
					help="Project name where the IoT device is being registered")
parser.add_argument('-f', '--function',
					type=str,
					required=True,
					metavar="FunctionType",
					help="Function type of the IoT device (e.g. temperature)")
parser.add_argument('-l', '--location',
					type=str,
					required=True,
					metavar="Location",
					help="Location of the IoT device being registered")
args = parser.parse_args()

# Parse connection configuration values
config = configparser.ConfigParser()
config.read(args.config)
topic = config["SETTINGS"]["IOT_TOPIC"]
iot_endpoint = config["SETTINGS"]["IOT_ENDPOINT"]
print(iot_endpoint)
root_cert_path = join(config["SETTINGS"]["SECURE_CERT_PATH"], config["SETTINGS"]["ROOT_CERT"])
print(root_cert_path)
private_key_path = join(config["SETTINGS"]["SECURE_CERT_PATH"], config["SETTINGS"]["SECURE_KEY"])
print(private_key_path)
claim_cert_path = join(config["SETTINGS"]["SECURE_CERT_PATH"], config["SETTINGS"]["CLAIM_CERT"])
print(claim_cert_path)
provisioning_template_name = config["SETTINGS"]["PROVISIONING_TEMPLATE_NAME"]
# Gather the UUID machine-id from your Linux device
with open("/etc/machine-id") as file:
	machine_uuid = file.readline().rstrip()

# Establish connection to your AWS account's IoT endpoint
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

mqtt_connection = mqtt_connection_builder.mtls_from_path(
	endpoint=iot_endpoint,
	cert_filepath=claim_cert_path,
	pri_key_filepath=private_key_path,
	client_bootstrap=client_bootstrap,
	ca_filepath=root_cert_path,
	client_id=machine_uuid,
	on_connection_interrupted=on_connection_interrupted,
	on_connection_resumed=on_connection_resumed,
	clean_session=False,
	keep_alive_secs=6)

print(f"Connecting to {iot_endpoint} with client ID '{machine_uuid}'...")
connected_future = mqtt_connection.connect()
identity_client = iotidentity.IotIdentityClient(mqtt_connection)

# Wait for connection to be fully established.
connected_future.result()
print("Connected!")

######################################################
# Create Certificate

# Subscribe to four AWS-managed topics required for obtaining a certificate issued by the fleet provisioning method
createkeysandcertificate_subscription_request = iotidentity.CreateKeysAndCertificateSubscriptionRequest()
print("Subscribing to CreateKeysAndCertificate Accepted topic...")
createkeysandcertificate_subscribed_accepted_future, _ = identity_client.subscribe_to_create_keys_and_certificate_accepted(
	request=createkeysandcertificate_subscription_request,
	qos=mqtt.QoS.AT_LEAST_ONCE,
	callback=createkeysandcertificate_execution_accepted)

# Wait for subscription to succeed
createkeysandcertificate_subscribed_accepted_future.result()

print("Subscribing to CreateKeysAndCertificate Rejected topic...")
createkeysandcertificate_subscribed_rejected_future, _ = identity_client.subscribe_to_create_keys_and_certificate_rejected(
	request=createkeysandcertificate_subscription_request,
	qos=mqtt.QoS.AT_LEAST_ONCE,
	callback=createkeysandcertificate_execution_rejected)

# Wait for subscription to succeed
createkeysandcertificate_subscribed_rejected_future.result()

registerthing_subscription_request = iotidentity.RegisterThingSubscriptionRequest(provisioning_template_name)
print("Subscribing to RegisterThing Accepted topic...")
registerthing_subscribed_accepted_future, _ = identity_client.subscribe_to_register_thing_accepted(
	request=registerthing_subscription_request,
	qos=mqtt.QoS.AT_LEAST_ONCE,
	callback=registerthing_execution_accepted)

# Wait for subscription to succeed
registerthing_subscribed_accepted_future.result()

print("Subscribing to RegisterThing Rejected topic...")
registerthing_subscribed_rejected_future, _ = identity_client.subscribe_to_register_thing_rejected(
	request=registerthing_subscription_request,
	qos=mqtt.QoS.AT_LEAST_ONCE,
	callback=registerthing_execution_rejected)
# Wait for subscription to succeed
registerthing_subscribed_rejected_future.result()


# Publish message to CreateKeysAndCertificate and save the credentials returned to disk
print("Publishing to CreateKeysAndCertificate...")
publish_future = identity_client.publish_create_keys_and_certificate(request=iotidentity.CreateKeysAndCertificateRequest(), qos=mqtt.QoS.AT_LEAST_ONCE)
publish_future.add_done_callback(on_publish_create_keys_and_certificate)


wait_for_create_keys_and_certificate_response()

if create_keys_and_certificate_response is None:
	raise Exception('CreateKeysAndCertificate API did not succeed')


######################################################
# Register thing

register_thing_request = iotidentity.RegisterThingRequest(
	template_name=provisioning_template_name,
	certificate_ownership_token=create_keys_and_certificate_response.certificate_ownership_token,
	parameters={"SerialNumber": machine_uuid,
				"ProjectName": args.project,
				"FunctionType": args.function,
				"Location": args.location})

print("Publishing to RegisterThing topic...")
registerthing_publish_future = identity_client.publish_register_thing(register_thing_request, mqtt.QoS.AT_LEAST_ONCE)
registerthing_publish_future.add_done_callback(on_publish_register_thing)

wait_for_register_thing_response()

if register_thing_response is None:
	raise Exception('Reigster Thing did not succeed')

######################################################
# Save long-term credentials to disk and create a config file defining variables for these files

long_term_credentials_path = join(config["SETTINGS"]["SECURE_CERT_PATH"], "permanent_cert/")
makedirs(long_term_credentials_path, exist_ok=True)

claim_cert_long_term_path = join(long_term_credentials_path, f"{machine_uuid}-certificate.pem.crt")
with open(claim_cert_long_term_path, "w") as outfile:
	outfile.write(create_keys_and_certificate_response.certificate_pem)

private_key_long_term_path = join(long_term_credentials_path, f"{machine_uuid}-private.pem.key")
with open(private_key_long_term_path, "w") as outfile:
	outfile.write(create_keys_and_certificate_response.private_key)

root_cert_long_term_path = join(long_term_credentials_path, config["SETTINGS"]["ROOT_CERT"])
shutil.copy2(root_cert_path, root_cert_long_term_path)

perm_config = configparser.ConfigParser()
perm_config.optionxform = str  # Maintains capitalization of variables: https://stackoverflow.com/questions/1611799/preserve-case-in-configparser
perm_config["SETTINGS"] = {
	"SECURE_CERT_PATH": long_term_credentials_path,
	"ROOT_CERT": root_cert_long_term_path,
	"CLAIM_CERT": claim_cert_long_term_path,
	"SECURE_KEY": private_key_long_term_path,
	"IOT_ENDPOINT": iot_endpoint,
	"IOT_TOPIC": topic,
	"DEVICE_PROJECT_NAME": args.project,
	"DEVICE_FUNCTION_TYPE": args.function,
	"DEVICE_LOCATION": args.location
}
with open(join(long_term_credentials_path, "perm_config.ini"), "w") as outfile:
	perm_config.write(outfile)


sys.exit("Success")
