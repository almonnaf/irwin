import logging
from flask import Blueprint, request, jsonify, json, Response

default_responses = {
    'success': Response(
        response=json({
            'success': True,
            'message': 'action completed successfully'
            }),
        status=200,
        mimetype='application/json'
    ),
    'bad_request': Response(
        response=json({
            'success': False,
            'message': 'bad request'
            }),
        status=200,
        mimetype='application/json')
}

def buildApiBlueprint(env):
    apiBlueprint = Blueprint('Api', __name__, url_prefix='/api')

    @apiBlueprint.route('/request_job', methods=['GET', 'POST'])
    def api_request_job():
        req = request.get_json(silent=True)

        account, authorised = env.auth.authoriseReq(req, 'request_job')

        if authorised:
            logging.info(str(account) + ' is authorised')
            return env.queue.nextDeepAnalysis(account.id)

    @apiBlueprint.route('/complete_job', method=['GET', 'POST'])
    def api_complete_job():
        req = request.get_json(silent=True)

        account, authorised = env.auth.authoriseReq(req, 'complete_job')

        if authorised:
            analysisId = req.get('id')
            logging.info(str(account) + ' requested to complete job ' + analysisId)
            if analysisId is not None:
                env.gameApi.insertAnalysedGames(req.get('game_analyses'))
                env.queue.queueNerualAnalysis(analysisId)
                env.queue.completeEngineAnalysis(analysisId)
                return default_responses['success']
        return default_responses['bad_request']