# -*- coding: utf-8 -*-.

from flask import Flask, request, abort, Response
from datetime import datetime as dt
import dateutil.parser
from pymongo import MongoClient
import pandas as pd
from bson import json_util
import json

app = Flask(__name__)


def _connect_mongo(db, host='localhost', port=27017, username=None, password=None):
    """ A util for making a connection to mongo """

    if username and password:
        mongo_uri = 'mongodb://%s:%s@%s:%s/%s' % (
            username, password, host, port, db)
        conn = MongoClient(mongo_uri)
    else:
        conn = MongoClient(host, port)

    return conn[db]


def _read_mongo(db, collection, query={}, query_args=None, no_id=True, df=False):
    """ Read from Mongo and Store into DataFrame """

    # Connect to MongoDB
    db = _connect_mongo(db=db)

    # Make a query to the specific DB and Collection
    cursor = db[collection].find(query, query_args)

    if df:
        # Expand the cursor and construct the DataFrame
        df = pd.DataFrame(list(cursor))

        # Delete the _id
        if no_id and '_id' in df.keys().tolist():
            del df['_id']

        return df
    return list(cursor)


def _process_channel_program(shows):
    today = dt.today()
    future_shows = []
    for show in shows:
        if dateutil.parser.parse(show['date']).date() == today.date():
            dailyShows = []
            for j in xrange(len(show['dailyShows'])):
                if dateutil.parser.parse(show['dailyShows'][j]['endTime']) >= today:
                    dailyShows.append(show['dailyShows'][j])
            show.update({'dailyShows': dailyShows})
            future_shows.append(show)
        if dateutil.parser.parse(show['date']).date() > today.date():
            future_shows.append(show)
    return future_shows


def _process_today_shows(shows):
    today = dt.today()
    for show in shows:
        if dateutil.parser.parse(show['date']).date() == today.date():
            dailyShows = []
            for j in xrange(len(show['dailyShows'])):
                if dateutil.parser.parse(show['dailyShows'][j]['endTime']) >= today:
                    dailyShows.append(show['dailyShows'][j])
            return dailyShows


def _process_current_shows(shows):
    today = dt.today()
    dailyShows = []
    for show in shows:
        if dateutil.parser.parse(show['date']).date() >= today.date():
            for dshow in show['dailyShows']:
                if dateutil.parser.parse(dshow['endTime']) >= today:
                    dailyShows.append(dshow)
    return dailyShows[:3]


def _process_channel_content_of(shows, showName):
    channel_content = []
    for show in shows:
        dailyShows = []
        for dshow in show['dailyShows']:
            if dshow['showName'].encode('utf-8') == showName.encode('utf-8'):
                dailyShows.append(dshow)
        if dailyShows:
            show.update({'dailyShows': dailyShows})
            channel_content.append(show)
    return channel_content


def _process_channel_content_by(shows, genre):
    channel_content = []
    for show in shows:
        dailyShows = []
        for dshow in show['dailyShows']:
            if dshow['genre'].encode('utf-8') == genre.encode('utf-8'):
                dailyShows.append(dshow)
        if dailyShows:
            show.update({'dailyShows': dailyShows})
            channel_content.append(show)
    return channel_content


def _process_shows_content_of(shows):
    today = dt.today()
    tvguide = []
    for show in shows:
        if dateutil.parser.parse(show['endTime']) >= today:
            tvguide.append(show)
    return tvguide


@app.route('/api/get_channels', methods=['GET'])
def getChannelsList():
    channels = _read_mongo('tv_guide', 'channels', query_args={
        '_id': False, 'channelName': True, 'channelLogo': True})
    return Response(response=json.dumps(dict(result=channels), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_channel_program', methods=['GET'])
def getChannelProgram():
    channelName = request.args.get('name')
    if (not channelName):
        abort(500)
    channelProgram = _read_mongo('tv_guide', 'channels', {
        'channelName': channelName}, {'_id': False}, df=True)
    channelProgram['shows'] = channelProgram['shows'].apply(
        _process_channel_program, 1)
    channelProgram = channelProgram.to_dict('records')
    return Response(response=json.dumps(dict(result=channelProgram), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_today_shows', methods=['GET'])
def getTodayShows():
    channels = _read_mongo('tv_guide', 'channels', df=True)
    channels['shows'] = channels['shows'].apply(_process_today_shows, 1)
    channels = channels[channels['shows'].str.len() !=
                        0].reset_index(drop=True)
    channels = channels.to_dict('records')
    return Response(response=json.dumps(dict(result=channels), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_current_shows', methods=['GET'])
def getCurrentShows():
    channels = _read_mongo('tv_guide', 'channels', df=True)
    channels['shows'] = channels['shows'].apply(_process_current_shows, 1)
    channels = channels.dropna(0, subset=['shows']).reset_index(drop=True)
    channels = channels.to_dict('records')
    return Response(response=json.dumps(dict(result=channels), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_channel_content_of', methods=['GET'])
def getChannelContentOf():
    showName = request.args.get('name')
    if (not showName):
        abort(500)
    channels = _read_mongo('tv_guide', 'channels', df=True)
    channels['shows'] = channels['shows'].apply(
        lambda x: _process_channel_content_of(x, showName), 1)
    channels = channels[channels['shows'].str.len() !=
                        0].reset_index(drop=True)
    channels = channels.to_dict('records')
    return Response(response=json.dumps(dict(result=channels), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_channel_content_by', methods=['GET'])
def getChannelContentBy():
    genre = request.args.get('genre')
    if (not genre):
        abort(500)
    channels = _read_mongo('tv_guide', 'channels', df=True)
    channels['shows'] = channels['shows'].apply(
        lambda x: _process_channel_content_by(x, genre), 1)
    channels = channels[channels['shows'].str.len() !=
                        0].reset_index(drop=True)
    channels = channels.to_dict('records')
    return Response(response=json.dumps(dict(result=channels), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_show_content_of', methods=['GET'])
def getShowContentOf():
    showName = request.args.get('name')
    if (not showName):
        abort(500)
    show = _read_mongo('tv_guide', 'shows', {
                       'showName': showName}, {'_id': False}, df=True)
    show['tvguide'] = show['tvguide'].apply(_process_shows_content_of, 1)
    youtube_show = _read_mongo('tv_guide', 'youtube_shows', {
        'showName': showName}, {'_id': False}, df=True)
    if(len(youtube_show.index) > 0):
        show = pd.merge(show,
                        youtube_show,
                        left_on=['showName'],
                        right_on=['showName'],
                        how='left',
                        sort=False)
    show = show.to_dict('records')
    return Response(response=json.dumps(dict(result=show), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


@app.route('/api/get_show_content_by', methods=['GET'])
def getShowContentBy():
    showType = request.args.get('type')
    if showType:
        show = _read_mongo('tv_guide', 'shows', {'showType': showType}, {
                           '_id': False, 'showName': True, 'showImage': True})
    else:
        show = _read_mongo('tv_guide', 'shows', {}, {
                           '_id': False, 'showName': True, 'showImage': True})
    return Response(response=json.dumps(dict(result=show), default=json_util.default),
                    headers={'Content-Type': 'application/json; charset=utf-8'},
                    status=200)


if __name__ == '__main__':
    app.run('0.0.0.0')
