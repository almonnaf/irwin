from collections import namedtuple

class GameAnalysisActivation(namedtuple('GameAnalysisActivation', ['id', 'userId', 'engine', 'length', 'prediction'])):
    @staticmethod
    def fromGamesAnalysisandPrediction(gameAnalysis, prediction, engine):
        return GameAnalysisActivation(
            id = gameAnalysis.id,
            userId = gameAnalysis.userId,
            engine = engine,
            length = len(gameAnalysis.moveAnalyses),
            prediction = prediction)

class GameAnalysisActivationBSONHandler:
    @staticmethod
    def reads(bson):
        return GameAnalysisActivation(
            id = bson['_id'],
            userId = bson['userId'],
            engine = bson['engine'],
            length = bson['length'],
            prediction = bson['prediction'])

    @staticmethod
    def writes(cga):
        return {
            '_id': cga.id,
            'userId': cga.userId,
            'engine': cga.engine,
            'length': cga.length,
            'prediction': cga.prediction
        }

class GameAnalysisActivationDB(namedtuple('GameAnalysisActivationDB', ['confidentGameAnalysisPivotColl'])):
    def byUserId(self, userId):
        return [GameAnalysisActivationBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'userId': userId})]

    def byEngineAndPrediction(self, engine, prediction):
        if engine:
            return [GameAnalysisActivationBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'prediction': {'$gte': prediction}})]
        return [GameAnalysisActivationBSONHandler.reads(bson) for bson in self.confidentGameAnalysisPivotColl.find({'engine': engine, 'prediction': {'$lte': prediction}})]

    def write(self, cga): # Game
        self.confidentGameAnalysisPivotColl.update_one({'_id': cga.id}, {'$set': GameAnalysisActivationBSONHandler.writes(cga)}, upsert=True)

    def lazyWriteMany(self, cgas):
        [self.write(cga) for cga in cgas]