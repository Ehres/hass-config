
try:
    from .const import (
        __nameMyEnedis__,
    )

except ImportError:
    from const import (
        __nameMyEnedis__,
    )
import logging
log = logging.getLogger(__nameMyEnedis__)
waitCall = 1  # 1 secondes

class myCall:
    def __init__(self):
        self._lastAnswer = None
        self._contentType = "application/json"
        self._contentHeaderMyEnedis = 'home-assistant-myEnedis'
        self._serverName = "https://enedisgateway.tech/api"
        pass

    def setParam( self, PDL_ID, token, version):
        self._PDL_ID, self._token, self._version = PDL_ID, token, version

    def getDefaultHeader(self):
        return {
            'Authorization': self._token,
            'Content-Type': self._contentType,
            'call-service': self._contentHeaderMyEnedis,
            'ha_sensor_myenedis_version': self._version,
        }

    def setLastAnswer(self, lastanswer):
        self._lastAnswer = lastanswer

    def getLastAnswer(self):
        return self._lastAnswer

    def post_and_get_json(self, url, params=None, data=None, headers=None):
        try:
            import time
            time.sleep( waitCall )
            import json, requests
            session = requests.Session()
            session.verify = True
            response = session.post(url, params=params, data=json.dumps(data), headers=headers, timeout=30)
            response.raise_for_status()
            dataAnswer = response.json()
            self.setLastAnswer(dataAnswer)
            #print("ici", params, headers, data)
            #raise(requests.exceptions.Timeout) # pour raiser un timeout de test ;)
            return dataAnswer
        except requests.exceptions.Timeout as error:
            response = {"enedis_return": {"error": "UNKERROR_002"}}
            self.setLastAnswer(response)
            return response
        except requests.exceptions.HTTPError as error:
            if ( "ADAM-ERR0069" not in response.text ) and \
                    ( "__token_refresh_401" not in response.text ):
                log.error("*" * 60)
                log.error("header : %s " % (headers))
                log.error("params : %s " % (params))
                log.error("data : %s " % (json.dumps(data)))
                log.error("Error JSON : %s " % (response.text))
                log.error("*" * 60)
            #with open('error.json', 'w') as outfile:
            #    json.dump(response.json(), outfile)
            dataAnswer = response.json()
            self.setLastAnswer(dataAnswer)
            return dataAnswer

    def getDataPeriod(self, deb, fin ):
        if (fin is not None):
            log.info("--get dataPeriod : %s => %s --" % (deb, fin))
            payload = {
                'type': 'daily_consumption',
                'usage_point_id': self._PDL_ID,
                'start': '%s' % (deb),
                'end': '%s' % (fin),
            }
            headers = self.getDefaultHeader()
            dataAnswer = self.post_and_get_json(self._serverName, data=payload, headers=headers)
            callDone = True
        else:
            # pas de donnée
            callDone = False
            dataAnswer = ""
        return dataAnswer, callDone

    def getDataPeriodConsumptionMaxPower(self, deb, fin):
        if (fin is not None):
            log.info("--get dataPeriod : %s => %s --" % (deb, fin))
            payload = {
                'type': 'daily_consumption_max_power',
                'usage_point_id': self._PDL_ID,
                'start': '%s' % (deb),
                'end': '%s' % (fin),
            }
            headers = self.getDefaultHeader()
            dataAnswer = self.post_and_get_json(self._serverName, data=payload, headers=headers)
            callDone = True
        else:
            # pas de donnée
            callDone = False
            dataAnswer = ""
        self.setLastAnswer(dataAnswer)
        return dataAnswer, callDone

    def getDataProductionPeriod(self, deb, fin):
        if (fin is not None):
            payload = {
                'type': 'daily_production',
                'usage_point_id': self._PDL_ID,
                'start': '%s' % (deb),
                'end': '%s' % (fin),
            }
            headers = self.getDefaultHeader()
            dataAnswer = self.post_and_get_json(self._serverName, data=payload, headers=headers)
            callDone = True
        else:
            # pas de donnée
            callDone = False
            dataAnswer = ""
        self.setLastAnswer(dataAnswer)
        return dataAnswer, callDone

    def getDataPeriodCLC(self, deb, fin ):
        if (fin is not None):
            payload = {
                'type': 'consumption_load_curve',
                'usage_point_id': self._PDL_ID,
                'start': '%s' % (deb),
                'end': '%s' % (fin),
            }
            headers = self.getDefaultHeader()
            dataAnswer = self.post_and_get_json(self._serverName, data=payload, headers=headers)
            callDone = True
        else:
            # pas de donnée
            callDone = False
            dataAnswer = ""
        self.setLastAnswer(dataAnswer)
        return dataAnswer, callDone

    def getDataContract(self):
        payload = {
            'type': 'contracts',
            'usage_point_id': self._PDL_ID,
        }
        headers = self.getDefaultHeader()
        dataAnswer = self.post_and_get_json(self._serverName, data=payload, headers=headers)
        return dataAnswer
