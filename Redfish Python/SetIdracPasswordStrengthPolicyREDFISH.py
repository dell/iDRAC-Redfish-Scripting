#!/usr/bin/python3
#
# SetIdracPasswordStrengthPolicyREDFISH. Python script using Redfish API with Dell OEM extension to get or set the iDRAC password strength policy minimum score.
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2017, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import argparse
import getpass
import json
import logging
import requests
import sys
import warnings

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser(description="Python script using Redfish API with Dell OEM extension to get or set the iDRAC password strength policy minimum score. Supported set values are 0, 1, 2 and 3.")
parser.add_argument('-ip',help='iDRAC IP address', required=False)
parser.add_argument('-u', help='iDRAC username', required=False)
parser.add_argument('-p', help='iDRAC password. If you do not pass in argument -p, script will prompt to enter user password which will not be echoed to the screen.', required=False)
parser.add_argument('-x', help='Pass in X-Auth session token for executing Redfish calls. All Redfish calls will use X-Auth token instead of username/password', required=False)
parser.add_argument('--ssl', help='SSL cert verification for all Redfish calls, pass in value "true" or "false". By default, this argument is not required and script ignores validating SSL cert for all Redfish calls.', required=False)
parser.add_argument('--script-examples', help='Get executing script examples', action="store_true", dest="script_examples", required=False)
parser.add_argument('--get', help='Get current iDRAC password strength policy minimum score.', action="store_true", required=False)
parser.add_argument('--set', help='Set iDRAC password strength policy minimum score. Supported values are 0, 1, 2 or 3.', required=False)
parser.add_argument('--attribute-name', help='Optional override for the iDRAC password strength policy attribute name if automatic discovery does not locate the correct attribute.', dest="attribute_name", required=False)

args = vars(parser.parse_args())
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

PASSWORD_SCORE_MAP = {
    0: 'No protection',
    1: 'Weak protection',
    2: 'Medium protection',
    3: 'Strong protection'
}

PASSWORD_SCORE_ALIASES = {
    0: ['No protection', 'No Protection'],
    1: ['Weak protection', 'Weak Protection'],
    2: ['Medium protection', 'Medium Protection'],
    3: ['Strong protection', 'Strong Protection']
}


def script_examples():
    print("""\n- SetIdracPasswordStrengthPolicyREDFISH.py -ip 192.168.0.120 -u root -p calvin --get, this example will get the current iDRAC password strength policy minimum score.
    \n- SetIdracPasswordStrengthPolicyREDFISH.py -ip 192.168.0.120 -u root -p calvin --set 0, this example will set the iDRAC password strength policy minimum score to 0 (No protection).
    \n- SetIdracPasswordStrengthPolicyREDFISH.py -ip 192.168.0.120 -u root -p calvin --set 3, this example will set the iDRAC password strength policy minimum score to 3 (Strong protection).
    \n- SetIdracPasswordStrengthPolicyREDFISH.py -ip 192.168.0.120 -x 983d154b4a125c7ae3838b8e32256b78 --set 1, this example shows setting the iDRAC password strength policy minimum score using an iDRAC X-auth token session.""")
    sys.exit(0)


def redfish_get(uri):
    if args["x"]:
        return requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, headers={'X-Auth-Token': args["x"]})
    return requests.get('https://%s/%s' % (idrac_ip, uri), verify=verify_cert, auth=(idrac_username, idrac_password))


def redfish_patch(uri, payload):
    headers = {'content-type': 'application/json'}
    if args["x"]:
        headers['X-Auth-Token'] = args["x"]
        return requests.patch('https://%s/%s' % (idrac_ip, uri), data=json.dumps(payload), headers=headers, verify=verify_cert)
    return requests.patch('https://%s/%s' % (idrac_ip, uri), data=json.dumps(payload), headers=headers, verify=verify_cert, auth=(idrac_username, idrac_password))


def check_supported_idrac_version():
    response = redfish_get('redfish/v1/Managers/iDRAC.Embedded.1')
    if response.status_code == 401:
        logging.warning("\n- WARNING, status code %s returned. Incorrect iDRAC username/password or invalid privilege detected." % response.status_code)
        sys.exit(0)
    if response.status_code != 200:
        logging.warning("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit(0)


def get_server_generation():
    global idrac_version
    response = redfish_get('redfish/v1/Managers/iDRAC.Embedded.1?$select=Model')
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    elif response.status_code != 200:
        logging.warning("\n- WARNING, unable to get current iDRAC version installed")
        sys.exit(0)
    if "12" in data["Model"] or "13" in data["Model"]:
        idrac_version = 8
    elif "14" in data["Model"] or "15" in data["Model"] or "16" in data["Model"]:
        idrac_version = 9
    else:
        idrac_version = 10


def get_attribute_resource_uri():
    return 'redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1'


def get_registry_entries():
    response = redfish_get('redfish/v1/Registries/ManagerAttributeRegistry/ManagerAttributeRegistry.v1_0_0.json')
    data = response.json()
    if response.status_code != 200:
        logging.error("\n- FAIL, status code %s returned for GET command. Detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    return data['RegistryEntries']['Attributes']


def get_version_candidate_names():
    if idrac_version >= 10:
        return [
            'Users.1.MinimumScore',
            'Users.1.PasswordMinimumScore',
            'Users.1.PasswordStrengthMinimumScore',
            'AccountSecurity.1.MinimumScore',
            'AccountSecurity.1.PasswordMinimumScore'
        ]
    return [
        'Users.1.MinimumScore',
        'Users.1.PasswordMinimumScore',
        'Users.1.PasswordStrengthMinimumScore',
        'PasswordPolicy.1.MinimumScore',
        'PasswordSettings.1.MinimumScore'
    ]


def score_registry_entry(entry):
    entry_text = json.dumps(entry).lower()
    score = 0
    if 'password' in entry_text:
        score += 3
    if 'minimum score' in entry_text:
        score += 5
    if 'strength' in entry_text:
        score += 4
    if 'policy' in entry_text:
        score += 2
    if 'simple policy' in entry_text or 'regular expression' in entry_text:
        score += 2
    if 'users.1.' in entry_text:
        score += 2
    if 'score' in entry_text:
        score += 1
    return score


def get_entry_attribute_name(entry):
    for key in ('AttributeName', 'Name', 'Attribute'):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    for value in entry.values():
        if isinstance(value, str) and '.' in value and 'password' in value.lower():
            return value
    return None


def resolve_password_policy_attribute_name():
    if args['attribute_name']:
        logging.info("\n- INFO, using attribute override \"%s\"" % args['attribute_name'])
        return args['attribute_name']

    registry_entries = get_registry_entries()
    candidate_names = get_version_candidate_names()
    for entry in registry_entries:
        attribute_name = get_entry_attribute_name(entry)
        if attribute_name in candidate_names:
            logging.info("\n- INFO, resolved password strength policy attribute \"%s\" using iDRAC%s candidate list" % (attribute_name, idrac_version))
            return attribute_name

    best_match = None
    best_score = 0
    for entry in registry_entries:
        entry_score = score_registry_entry(entry)
        attribute_name = get_entry_attribute_name(entry)
        if not attribute_name:
            continue
        if entry_score > best_score:
            best_match = attribute_name
            best_score = entry_score

    if best_match and best_score >= 8:
        logging.info("\n- INFO, resolved password strength policy attribute \"%s\" using registry text match" % best_match)
        return best_match

    logging.error("\n- FAIL, unable to locate the iDRAC password strength policy attribute in the manager attribute registry. Re-run the script with --attribute-name once you identify the correct attribute name from GetIdracLcSystemAttributesREDFISH.py or the manager attribute registry.")
    sys.exit(0)


def get_attribute_payload():
    response = redfish_get(get_attribute_resource_uri())
    data = response.json()
    if response.status_code == 401:
        logging.error("\n- ERROR, status code 401 detected, check to make sure your iDRAC script session has correct username/password credentials or if using X-auth token, confirm the session is still active.")
        sys.exit(0)
    if response.status_code != 200:
        logging.error("\n- FAIL, status code %s returned for GET command. Detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)
    return data


def normalize_score(value):
    try:
        return int(value)
    except:
        return value


def normalize_policy_label(value):
    if not isinstance(value, str):
        return None
    return ' '.join(value.strip().lower().split())


def get_score_from_value(value):
    normalized_value = normalize_score(value)
    if isinstance(normalized_value, int) and normalized_value in PASSWORD_SCORE_MAP:
        return normalized_value
    normalized_label = normalize_policy_label(value)
    if normalized_label is None:
        return None
    for score_value, aliases in PASSWORD_SCORE_ALIASES.items():
        for alias in aliases:
            if normalize_policy_label(alias) == normalized_label:
                return score_value
    return None


def get_display_value(value):
    score_value = get_score_from_value(value)
    if score_value is None:
        return str(value)
    return '%s (%s)' % (score_value, PASSWORD_SCORE_MAP[score_value])


def get_registry_allowable_values(entry):
    allowable_values = []
    if not entry:
        return allowable_values
    for key in ('Value', 'Values', 'AllowableValues', 'PossibleValues'):
        value = entry.get(key)
        if isinstance(value, list):
            allowable_values.extend(value)
    for value in entry.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, (str, int)):
                    allowable_values.append(item)
    deduped_values = []
    for value in allowable_values:
        if value not in deduped_values:
            deduped_values.append(value)
    return deduped_values


def resolve_payload_value(requested_score, current_value, registry_entry):
    normalized_current_value = normalize_score(current_value)
    allowable_values = get_registry_allowable_values(registry_entry)
    for alias in PASSWORD_SCORE_ALIASES[requested_score]:
        for allowable_value in allowable_values:
            if isinstance(allowable_value, str) and normalize_policy_label(allowable_value) == normalize_policy_label(alias):
                return allowable_value
    if isinstance(normalized_current_value, str) and get_score_from_value(normalized_current_value) is not None:
        return PASSWORD_SCORE_ALIASES[requested_score][-1]
    return requested_score


def get_current_password_strength_policy(attribute_name):
    data = get_attribute_payload()
    attributes = data['Attributes']
    if attribute_name not in attributes:
        logging.error("\n- FAIL, password strength policy attribute \"%s\" was not found in current iDRAC attributes. Confirm the correct attribute name using the manager attribute registry." % attribute_name)
        sys.exit(0)
    current_value = attributes[attribute_name]
    logging.info("\n- Password Strength Policy Information -")
    logging.info("- iDRAC Version Detected: %s" % idrac_version)
    logging.info("- Attribute Name: %s" % attribute_name)
    logging.info("- Current Minimum Score: %s" % get_display_value(current_value))


def get_registry_entry_for_attribute(attribute_name):
    for entry in get_registry_entries():
        if get_entry_attribute_name(entry) == attribute_name:
            return entry
    return None


def set_password_strength_policy(attribute_name):
    try:
        requested_score = int(args['set'])
    except:
        logging.error("\n- FAIL, invalid value entered for --set argument. Supported values are 0, 1, 2 or 3.")
        sys.exit(0)
    if requested_score not in PASSWORD_SCORE_MAP:
        logging.error("\n- FAIL, invalid value entered for --set argument. Supported values are 0, 1, 2 or 3.")
        sys.exit(0)

    registry_entry = get_registry_entry_for_attribute(attribute_name)
    if registry_entry:
        logging.info("\n- INFO, password strength policy attribute registry match detected for \"%s\"" % attribute_name)

    current_attributes = get_attribute_payload()['Attributes']
    current_value = current_attributes.get(attribute_name)
    payload_value = resolve_payload_value(requested_score, current_value, registry_entry)
    logging.info("- INFO, current password strength policy value detected as: %s" % get_display_value(current_value))
    logging.info("- INFO, setting password strength policy value to: %s" % get_display_value(payload_value))

    payload = {'Attributes': {attribute_name: payload_value}}
    response = redfish_patch(get_attribute_resource_uri(), payload)
    if response.status_code == 200:
        logging.info("\n- PASS, status code %s returned for PATCH command to set iDRAC password strength policy minimum score to %s (%s)" % (response.status_code, requested_score, PASSWORD_SCORE_MAP[requested_score]))
    else:
        data = response.json()
        logging.error("\n- FAIL, status code %s returned, password strength policy minimum score was not changed. Detailed error results: \n%s" % (response.status_code, data))
        sys.exit(0)

    data = get_attribute_payload()
    new_value = data['Attributes'].get(attribute_name)
    new_score = get_score_from_value(new_value)
    if new_score == requested_score:
        logging.info("- PASS, password strength policy minimum score successfully set to %s" % get_display_value(new_value))
    else:
        logging.error("- FAIL, password strength policy minimum score not set to %s (%s), current value is %s" % (requested_score, PASSWORD_SCORE_MAP[requested_score], get_display_value(new_value)))
        sys.exit(0)


if __name__ == "__main__":
    if args["script_examples"]:
        script_examples()
    if args["ip"] and (args["x"] or args["u"]):
        idrac_ip = args["ip"]
        idrac_username = args["u"]
        if args["p"]:
            idrac_password = args["p"]
        if not args["p"] and not args["x"] and args["u"]:
            idrac_password = getpass.getpass("\n- Argument -p not detected, pass in iDRAC user %s password: " % args["u"])
        if args["ssl"]:
            if args["ssl"].lower() == "true":
                verify_cert = True
            elif args["ssl"].lower() == "false":
                verify_cert = False
            else:
                verify_cert = False
        else:
            verify_cert = False
        check_supported_idrac_version()
        get_server_generation()
        if idrac_version < 9:
            logging.error("\n- FAIL, password strength policy configuration is only supported for iDRAC9 release 4.40.00.00 and newer, and iDRAC10 platforms.")
            sys.exit(0)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")
        sys.exit(0)

    if args['get']:
        password_policy_attribute_name = resolve_password_policy_attribute_name()
        get_current_password_strength_policy(password_policy_attribute_name)
    elif args['set']:
        password_policy_attribute_name = resolve_password_policy_attribute_name()
        set_password_strength_policy(password_policy_attribute_name)
    else:
        logging.error("\n- FAIL, invalid argument values or not all required parameters passed in. See help text or argument --script-examples for more details.")