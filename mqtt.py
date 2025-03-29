from paho.mqtt import client as mqtt
from pygame import time as time
from log import *

class MqttClient(Log):
    _RECONNECT_COUNT = 12  # Amount of reconnect attempts
    _RECONNECT_INTERVAL = 1  # Delay between reconnect attempts (s)
    _RECONNECT_MAX_INTERVAL = 1200  # Max interval amount (s)
    _RECONNECT_RATE = 2  # Multiply interval by {n} each attempt

    def __init__(self, client_id: str, host: str, username: str, password: str, port=1883):
        """
        :param client_id: The ID/Name of the client
        :param host: The IP address of the server
        :param username: The username of the server
        :param password: The password of the server
        :param port: The port of the server
        """
        super().__init__('Mqtt')
        self._client_id = client_id
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self._client_id)

        self.topics = {}  # Subscribed topics -> { 'topic': response() }

    def _on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            self.log(f"Connected to \"{self._host}\" with id \"{self._client_id}\"", LogLevel.INF)
        else:
            self.log(f"Failed to connect to \"{self._host}\"", LogLevel.ERR, "code: " + rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        self.log(f"Disconnected from \"{self._host}\"", LogLevel.WRN, "code: " + rc)
        count = 0
        delay = self._RECONNECT_INTERVAL
        while count < self._RECONNECT_COUNT:
            self.log(f"Reconnecting in {delay}s...", LogLevel.INF)
            time.wait(delay * 1000)

            try:
                client.reconnect()
                self.log("Reconnected successfully!", LogLevel.INF)
                return
            except Exception as e:
                self.handle("Reconnect failed. Retrying...", e)

            delay *= self._RECONNECT_RATE
            delay = min(delay, self._RECONNECT_MAX_INTERVAL)
            count += 1
        self.log(f"Reconnect failed, exiting...", LogLevel.ERR, "attempts: " + count)
        raise KeyboardInterrupt

    def _on_message(self, client, userdata, msg):
        for t in self.topics:  # Delegate message to functions
            if t == msg.topic:
                self.topics[t](client, userdata, msg)
                return

    def get_connected(self):
        return self._client.is_connected()

    def get_host(self):
        return self._host

    def get_port(self):
        return self._port

    def get_id(self):
        return self._client_id

    def connect(self):
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, self._client_id)
        self._client.username_pw_set(self._username, self._password)
        #self._client.will_set("miniplayer/mqtt/disconnected", payload=self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.connect(self._host, self._port)
        self._client.loop_start()
        #self.pub("miniplayer/mqtt/connected", payload=self._client_id)

    def disconnect(self):
        self._client.on_disconnect = None  # Do not attempt to reconnect
        self._client.disconnect()
        self.unsub_all()
        self._client.loop_stop()

    def unsub_all(self):
        for t in self.topics:
            self._client.unsubscribe(t)
        self.topics = {}
        self.log("Unsubscribed from all topics", LogLevel.INF)

    def unsub(self, topic: str or tuple):
        if type(topic) is str:  # Convert single to tuple
            topic = [topic]

        for t in topic:
            self._client.unsubscribe(t)
            if t in self.topics:
                self.topics.pop(t)
                self.log("Unsubscribed from " + t, LogLevel.INF)
            else:
                self.log(t + " was not subscribed to, cannot unsub", LogLevel.WRN)

    def sub(self, topic: str or tuple, response):
        if type(topic) is str:  # Convert single to tuple
            topic = [topic]

        for t in topic:
            if t not in self.topics:
                self._client.subscribe(t)
                self.topics.update({t: response})  # Insert to dict
                self.log("Subscribed to " + t, LogLevel.INF)
            else:
                self.log(t + " is already subscribed to", LogLevel.WRN)

    def pub(self, topic: str, payload: str or dict):
        msg = str(payload).replace("'", "\"")  # Convert single quotes to double (because of dict)
        self._client.publish(topic, payload=msg)
        self.log(f"Sent \"{msg}\" to {topic}", LogLevel.INF)
