from default_imports import *

from modules.game.Colour import Colour
from modules.game.Player import PlayerID
from modules.game.Blurs import Blurs, BlursBSONHandler
from modules.game.EngineEval import EngineEval, EngineEvalBSONHandler

from pymongo.collection import Collection

import math
import numpy as np

GameID = NewType('GameID', str)
Emt = NewType('Emt', int)
Blur = NewType('Blur', bool)
Analysis = NewType('Analysis', List[EngineEval])

MoveTensor = NewType('MoveTensor', List[Number])
GameTensor = NewType('GameTensor', List[MoveTensor])

class Game(NamedTuple('Game', [
        ('id', GameID),
        ('white', PlayerID),
        ('black', PlayerID),
        ('pgn', List[str]),
        ('emts', List[Emt]),
        ('whiteBlurs', Blurs),
        ('blackBlurs', Blurs),
        ('analysis', Analysis)
    ])):
    @staticmethod
    def fromDict(gid: GameID, playerId: PlayerID, d: Dict):
        pgn = d['pgn'].split(" ")
        white, black = None, None
        if d['color'] == 'white':
            white = playerId
        else:
            black = playerId
        return Game(
            id = gid,
            white = white,
            black = black,
            pgn = pgn,
            emts = d.get('emts'),
            whiteBlurs = Blurs.fromDict(d['blurs']['white'], math.ceil(len(pgn)/2)),
            blackBlurs = Blurs.fromDict(d['blurs']['black'], math.floor(len(pgn)/2)),
            analysis = [EngineEval.fromDict(a) for a in d.get('analysis', []) if a is not None]
        )

    @staticmethod
    def fromJson(json: Dict):
        """Returns a list of Game items from json json object from lichess api"""
        return [Game.fromDict(gid, json['user']['id'], g) for gid, g in json['games'].items() \
                 if g.get('initialFen') is None and g.get('variant') is None]

    def tensor(self, playerId: PlayerID) -> GameTensor:
        if self.analysis == [] or self.emts is None and (self.white == playerId or self.black == playerId):
            return None

        white = (self.white == playerId)
        blurs = self.whiteBlurs.moves if white else self.blackBlurs.moves

        analysis = self.analysis[1:] if white else self.analysis
        analysis = list(zip(analysis[0::2],analysis[1::2]))

        emts = self.emtsByColour(white)
        avgEmt = np.average(emts)
        tensors = [Game.moveTensor(a, b, e, avgEmt, white) for a, b, e in zip(analysis, blurs, emts)]
        tensors = (max(0, 100-len(tensors)))*[Game.nullMoveTensor()] + tensors
        return tensors[:100]

    def emtsByColour(self, colour: Colour) -> List[Emt]:
        return self.emts[(0 if colour else 1)::2]

    @staticmethod
    def moveTensor(analysis: Analysis, blur: Blur, emt: Emt, avgEmt: Number, colour: Colour) -> MoveTensor:
        return [
            analysis[1].winningChances(colour),
            (analysis[0].winningChances(colour) - analysis[1].winningChances(colour)),
            int(blur),
            emt,
            emt - avgEmt,
            100*((emt - avgEmt)/(avgEmt + 1e-8)),
        ]

    @staticmethod
    def nullMoveTensor() -> MoveTensor:
        return [0, 0, 0, 0, 0, 0]

    @staticmethod
    def ply(moveNumber: int, colour: Colour) -> int:
        return (2*(moveNumber-1)) + (0 if colour else 1)

    def getBlur(self, colour: Colour, moveNumber: int) -> Blur:
        if colour:
            return self.whiteBlurs.moves[moveNumber-1]
        return self.blackBlurs.moves[moveNumber-1]

class GameBSONHandler:
    @staticmethod
    def reads(bson: Dict) -> Game:
        return Game(
            id = bson['_id'],
            white = bson.get('white'),
            black = bson.get('black'),
            pgn = bson['pgn'],
            emts = bson['emts'],
            whiteBlurs = BlursBSONHandler.reads(bson['whiteBlurs']),
            blackBlurs = BlursBSONHandler.reads(bson['blackBlurs']),
            analysis = [EngineEvalBSONHandler.reads(a) for a in bson.get('analysis', [])])

    @staticmethod
    def writes(game: Game) -> Dict:
        return {
            '_id': game.id,
            'white': game.white,
            'black': game.black,
            'pgn': game.pgn,
            'emts': game.emts,
            'whiteBlurs': BlursBSONHandler.writes(game.whiteBlurs),
            'blackBlurs': BlursBSONHandler.writes(game.blackBlurs),
            'analysis': [EngineEvalBSONHandler.writes(a) for a in game.analysis],
            'analysed': len(game.analysis) > 0
        }

class GameDB(NamedTuple('GameDB', [
        ('gameColl', Collection)
    ])):
    def byId(self, _id: GameID) -> Opt[Game]:
        bson = self.gameColl.find_one({'_id': _id})
        return None if bson is None else GameBSONHandler.reads(bson)

    def byIds(self, ids: List[GameID]) -> List[Game]:
        return [GameBSONHandler.reads(g) for g in self.gameColl.find({'_id': {'$in': [i for i in ids]}})]

    def byPlayerId(self, playerId: PlayerID) -> List[Game]:
        return [GameBSONHandler.reads(g) for g in self.gameColl.find({"$or": [{"white": playerId}, {"black": playerId}]})]

    def byPlayerIdAndAnalysed(self, playerId: PlayerID, analysed: bool = True) -> List[Game]:
        return [GameBSONHandler.reads(g) for g in self.gameColl.find({"analysed": analysed, "$or": [{"white": playerId}, {"black": playerId}]})]

    def write(self, game: Game):
        self.gameColl.update_one({'_id': game.id}, {'$set': GameBSONHandler.writes(game)}, upsert=True)

    def lazyWriteMany(self, games: List[Game]):
        [self.write(g) for g in games]