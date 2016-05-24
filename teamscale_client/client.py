from __future__ import absolute_import
from __future__ import unicode_literals

import requests
from requests.auth import HTTPBasicAuth
import time

import simplejson as json

from teamscale_client.data import ServiceError, Baseline
from teamscale_client.utils import to_json

class TeamscaleClient:
    """Basic Python service client to access Teamscale's REST Api.

    Request handling done with:
    http://docs.python-requests.org/en/latest/

    Args:
        url (str): The url to Teamscale (including the port)
        username (str): The username to use for authentication
        password (str): The password/api key to use for authentication
        project (str): The project on which to work
        sslverify: See requests' verify parameter in http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification
    """

    def __init__(self, url, username, password, project, sslverify=True):
        self.url = url
        self.username = username
        self.auth_header = HTTPBasicAuth(username, password)
        self.project = project
        self.sslverify = sslverify

    def get(self, url, parameters=None):
        """Sends a get request to the given service url.

        Args:
            url (str):  The URL for which to execute a PUT request
            parameters (dict): parameters to attach to the url

        Returns:
            requests.Response: request's response

        Raises:
            ServiceError: If anything goes wrong
        """
        response = requests.get(url, params=parameters, auth=self.auth_header, verify=self.sslverify)
        if response.status_code != 200:
            raise ServiceError("ERROR: GET {url}: {r.status_code}:{r.text}".format(url=url, r=response))
        return response

    def put(self, url, json=None, parameters=None, data=None):
        """Sends a put request to the given service url with the json payload as content.

        Args:
            url (str):  The URL for which to execute a PUT request
            json: The Object to attach as content, will be serialized to json (only for object that can be serialized by default)
            parameters (dict): parameters to attach to the url
            data: The data object to be attached to the request

        Returns:
            requests.Response: request's response

        Raises:
            ServiceError: If anything goes wrong
        """
        response = requests.put(url, params=parameters, json=json, data=data, headers={'Content-Type': 'application/json'}, auth=self.auth_header, verify=self.sslverify)
        if response.status_code != 200:
            raise ServiceError("ERROR: PUT {url}: {r.status_code}:{r.text}".format(url=url, r=response))
        return response

    def add_findings_group(self, name, mapping_pattern):
        """Adds group of findings.

        Args:
            name (str): Name of group.
            mapping_pattern (str): Regular expression to match a finding's ``typeid`` in order to belong to this group.
        Returns:
            requests.Response: request's response
        """
        url = self.get_global_service_url('add-external-findings-group')
        payload = [{'groupName': name, 'mapping': mapping_pattern}]
        return self.put(url, payload)

    def add_finding_descriptions(self, descriptions):
        """Adds descriptions of findings.

        Args:
            descriptions (list): List of :class:`FindingDescription` to add to Teamscale.
        Returns:
            requests.Response: request's response
        """

        url = self.get_global_service_url('add-external-finding-descriptions')
        payload = [{'typeId': d.typeid, 'description': d.description, 'enablement': d.enablement} for d in descriptions]
        return self.put(url, payload)

    def update_findings_schema(self):
        """Triggers refresh of finding groups in analysis profiles."""
        url = self.get_global_service_url('update-findings-schema')
        return self.get(url, {'projects': self.project})

    def upload_findings(self, findings, timestamp, message, partition):
        """Uploads a list of findings

        Args:
            findings (List[:class:`data.FileFindings`]): the findings data 
            timestamp (datetime.datetime): timestamp for which to upload the findings
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the findings should be added (See also: :ref:`FAQ - Partitions<faq-partition>`).

        Returns:
            requests.Response: object generated by the request

        Raises:
            ServiceError: If anything goes wrong
        """
        return self._upload_external_data("add-external-findings", findings, timestamp, message, partition)

    def upload_metrics(self, metrics, timestamp, message, partition):
        """Uploads a list of metrics

        Args:
            metrics (List[:class:`data.MetricEntry`]): metrics data
            timestamp (datetime.datetime): timestamp for which to upload the metrics
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the metrics should be added (See also: :ref:`FAQ - Partitions<faq-partition>`).

        Returns:
            requests.Response: object generated by the upload request

        Raises:
            ServiceError: If anything goes wrong
        """
        return self._upload_external_data("add-external-metrics", metrics, timestamp, message, partition)

    def _upload_external_data(self, service_name, json_data, timestamp, message, partition):
        """Uploads externals data in json format

        Args:
            service_name (str): The service name to which to upload the data
            json_data: data in json format
            timestamp (datetime.datetime): timestamp (unix format) for which to upload the data
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the data should be added (See also: :ref:`FAQ - Partitions<faq-partition>`).

        Returns:
            requests.Response: object generated by the request

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_project_service_url(service_name)
        parameters = {
            "t": self._get_timestamp_ms(timestamp),
            "message": message,
            "partition": partition,
            "skip-session": "true",
            "adjusttimestamp": "true"
        }
        return self.put(service_url, parameters=parameters, data=to_json(json_data))

    def add_metric_descriptions(self, metric_descriptions):
        """Uploads metric definitions to Teamscale.

        Args:
            metric_descriptions (list[:class:`MetricDescription`]): List of metric descriptions to add to Teamscale.

        Returns:
            requests.Response: object generated by the request

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_global_service_url("add-external-metric-description")
        return self.put(service_url, data=to_json(metric_descriptions))

    def upload_coverage_data(self, coverage_files, coverage_format, timestamp, message, partition):
        """Upload coverage reports to Teamscale. It is expected that the given coverage report files can be read from the filesystem.

        Args:
            coverage_files (list): list of coverage filenames (strings!) that should be uploaded. Files must be readable.
            coverage_format  (constants.CoverageFormats): the format to use
            timestamp (datetime.datetime): timestamp (unix format) for which to upload the data
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the data should be added (See also: :ref:`FAQ - Partitions<faq-partition>`).

        Returns:
            requests.Response: object generated by the request

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_project_service_url("external-report")
        parameters = {
            "t": self._get_timestamp_ms(timestamp),
            "message": message,
            "partition": partition,
            "format": coverage_format,
            "adjusttimestamp": "true"
        }
        multiple_files = [('report', open(filename, 'rb')) for filename in coverage_files]
        response = requests.post(service_url, params=parameters, auth=self.auth_header, verify=self.sslverify, files=multiple_files)
        if response.status_code != 200:
            raise ServiceError("ERROR: GET {url}: {r.status_code}:{r.text}".format(url=service_url, r=response))
        return response

    def upload_architectures(self, architectures, timestamp, message):
        """Upload architectures to Teamscale. It is expected that the given architectures can be be read from the filesystem.

        Args:
            architectures (dict): mappping of teamscale paths to real architecture files that should be uploaded. Files must be readable.
            timestamp (datetime.datetime): timestamp (unix format) for which to upload the data
            message (str): The message to use for the generated upload commit

        Returns:
            requests.Response: object generated by the request

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_project_service_url("architecture-upload")
        parameters = {
            "t": self._get_timestamp_ms(timestamp),
            "message": message
        }
        multiple_files = [(path, open(filename, 'rb')) for path, filename in architectures.items()]
        response = requests.post(service_url, params=parameters, auth=self.auth_header, verify=self.sslverify, files=multiple_files)
        if response.status_code != 200:
            raise ServiceError("ERROR: GET {url}: {r.status_code}:{r.text}".format(url=service_url, r=response))
        return response

    def upload_none_code_metrics(self, metrics, timestamp, message, partition):
        """Uploads a list of none-code metrics

        Args:
            metrics (List[:class:`data.NoneCodeMetricEntry`]): metrics data
            timestamp (datetime.datetime): timestamp for which to upload the metrics
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the metrics should be added (See also: :ref:`FAQ - Partitions<faq-partition>`).

        Returns:
            requests.Response: object generated by the upload request

        Raises:
            ServiceError: If anything goes wrong
        """
        return self._upload_external_data("add-none-code-metrics", metrics, timestamp, message, partition)

    def get_baselines(self):
        """Retrieves a list of baselines from the server for the currently active project.

        Returns:
            List[:class:`data.Basenline`]): The list of baselines.

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_project_service_url("baselines")
        parameters = {
            "detail": True
        }
        headers = {'Accept' : 'application/json'}
        response = requests.get(service_url, params=parameters, auth=self.auth_header, verify=self.sslverify, headers=headers)
        if response.status_code != 200:
            raise ServiceError("ERROR: GET {url}: {r.status_code}:{r.text}".format(url=service_url, r=response))
        print response.text
        return [ Baseline(x['name'], x['description'], timestamp=x['timestamp']) for x in response.json() ]

    def add_baseline(self, baseline):
        """Adds a baseline to the currently active project.

        Args:
            baseline (data.Baseline): The baseline that is to be added

        Returns:
            requests.Response: object generated by the upload request

        Raises:
            ServiceError: If anything goes wrong
        """
        service_url = self.get_project_service_url("baselines")
        service_url += baseline.name
        return self.put(service_url, parameters={}, data=to_json(baseline))

    def _get_timestamp_ms(self, timestamp):
        """Returns the timestamp  in ms.

        Args:
            timestamp (datetime.datetime): The timestamp to convert

        Returns:
            int: timestamp in ms
        """
        timestamp_seconds = time.mktime(timestamp.timetuple())
        return int(timestamp_seconds * 1000)

    def get_global_service_url(self, service_name):
        """Returns the full url pointing to a global service.

        Args:
           service_name(str): the name of the service for which the url should be generated

        Returns:
            str: The full url
        """
        return "%s/%s/" % (self.url, service_name)

    def get_project_service_url(self, service_name):
        """Returns the full url pointing to a project service.

        Args:
           service_name(str): the name of the service for which the url should be generated

        Returns:
            str: The full url
        """
        return "{client.url}/p/{client.project}/{service}/".format(client=self, service=service_name)

    @classmethod
    def read_json_from_file(cls, file_path):
        """Reads JSON content from a file and parses it to ensure basic integrity.

        Args:
            file_path (str): File from which to read the JSON content.

        Returns:
            The parsed JSON data."""
        with open(file_path) as json_file:
            json_data = json.load(json_file)
            return json_data
