import requests
import threading
import json

class PlayerEngineStatusBus(threading.Thread):
  def __init__(self, playerDB, config, learner):
    threading.Thread.__init__(self)
    self.playerDB = playerDB
    self.token = config['api']['token']
    self.url = config['api']['url']
    self.learner = learner

  def run(self):
    while True and self.learner:
      r = requests.get(self.url + 'irwin/stream?api_key=' + self.token, stream=True)
      for line in r.iter_lines():
        lineDict = json.loads(line.decode("utf-8"))
        player = self.playerDB.byId(lineDict['user'])
        if player is not None:
          if lineDict['t'] == 'mark':
            self.playerDB.write(player.setEngine(lineDict['value']))
          elif lineDict['t'] == 'report' and player.engine == False:
            self.playerDB.write(player.setEngine(None))