import requests
import base64

class TeamscaleClient:
    """Basic Python service client to access Teamscale's REST Api.

    Request handling done with:
    http://docs.python-requests.org/en/latest/
    """

    def __init__(self, url, username, password, project):
        """Creates a new TeamscaleClient

        Args:
            url (str): The url to Teamscale (including the port)
            username (str): The username to use for authentication
            password (str): The password/api key to use for authentication
            project (str): The project on which to work
        """
        self.url = url
        self.username = username
        self.auth_header = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        self.project = project

    def put(self, url, json, parameters):
        """Sends a put request to the given service url with the json payload as content.

        Args:
            url (str):  The URL for which to execute a PUT request
            json: The JSON Object to attach as content
            parameters (dict): parameters to attach to the url

        Returns:
            requests.Response: request's response

        Raises:
            Exception: If anything goes wrong
        """
        response = requests.put(url, params=parameters, json=json, headers={'Content-Type':'application/json', "Authorization" : "Basic %s" % self.auth_header})
        if response.status_code != 200:
            raise Exception("ERROR: PUT "+url+": {}:{}".format(response.status_code, response.text))
        return response

    def upload_findings(self, findings, timestamp, message, partition):
        """Uploads a list of findings

        Args:
            findings: findings data in json format
            timestamp (int): timestamp (unix format) for which to upload the findings
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the findings should be added

        Returns:
            requests.Response: object generated by the request
        """
        return self._upload_external_data("add-external-findings", findings, timestamp, message, partition)

    def upload_metrics(self, metrics, timestamp, message, partition):
        """Uploads a list of metrics

        Args:
            metrics: metrics data in json format
            timestamp (int): timestamp (unix format) for which to upload the metrics
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the metrics should be added

        Returns:
            requests.Response: object generated by the upload request
        """
        return self._upload_external_data("add-external-metrics", metrics, timestamp, message, partition)

    def _upload_external_data(self, service_name, json_data, timestamp, message, partition):
        """Uploads externals data in json format

        Args:
            service_name (str): The service name to which to upload the data
            json_data: data in json format
            timestamp (int): timestamp (unix format) for which to upload the data
            message (str): The message to use for the generated upload commit
            partition (str): The partition's id into which the data should be added

        Returns:
            requests.Response: object generated by the request
        """
        service_url = self.get_project_service_url(service_name)
        parameters = {
            "t" : timestamp,
            "message" : message,
            "partition" : partition,
            "skip-session" : "true"
        }
        return self.put(service_url, json_data, parameters)



    def get_project_service_url(self, service_name):
        """Returns the full url pointing to a service.

        Args:
           service_name: the name of the service for which the url should be generated

        Returns:
            str: The full url
        """
        return "%s/p/%s/%s/" % (self.url, self.project, service_name)

