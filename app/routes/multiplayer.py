from flask import Blueprint, render_template, request
from flask_socketio import emit, join_room, leave_room
from app import socketio

multiplayer_bp = Blueprint('multiplayer', __name__)

ROOMS = {}

@multiplayer_bp.route('/')
def index():
    return render_template('multiplayer/room.html')

@socketio.on('join_race')
def handle_join(data):
    room = data.get('room', 'public-arena').strip() or 'public-arena'
    name = data.get('name', 'Pilot')
    sid = request.sid

    join_room(room)
    if room not in ROOMS:
        ROOMS[room] = {
            'text': "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.",
            'players': {},
            'status': 'lobby' # 'lobby', 'countdown', 'racing', 'finished'
        }

    ROOMS[room]['players'][sid] = {
        'id': sid,
        'name': name,
        'progress': 0,
        'wpm': 0,
        'finished': False,
        'place': None
    }

    emit('room_update', ROOMS[room], room=room)

@socketio.on('start_countdown')
def handle_countdown(data):
    room = data.get('room', 'public-arena')
    if room in ROOMS:
        ROOMS[room]['status'] = 'countdown'
        for sid in ROOMS[room]['players']:
            ROOMS[room]['players'][sid]['progress'] = 0
            ROOMS[room]['players'][sid]['wpm'] = 0
            ROOMS[room]['players'][sid]['finished'] = False
            ROOMS[room]['players'][sid]['place'] = None

        emit('race_countdown_started', {'status': 'countdown', 'text': ROOMS[room]['text']}, room=room)

@socketio.on('progress_update')
def handle_progress(data):
    room = data.get('room', 'public-arena')
    progress = data.get('progress', 0)
    wpm = data.get('wpm', 0)
    sid = request.sid

    if room in ROOMS and sid in ROOMS[room]['players']:
        ROOMS[room]['players'][sid]['progress'] = progress
        ROOMS[room]['players'][sid]['wpm'] = wpm

        if progress >= 100 and not ROOMS[room]['players'][sid]['finished']:
            ROOMS[room]['players'][sid]['finished'] = True
            # Determine placement
            finished_count = sum(1 for p in ROOMS[room]['players'].values() if p['finished'])
            ROOMS[room]['players'][sid]['place'] = finished_count
            emit('player_finished', {'name': ROOMS[room]['players'][sid]['name'], 'place': finished_count, 'wpm': wpm}, room=room)

        emit('race_progress', {'players': ROOMS[room]['players']}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for room, rdata in list(ROOMS.items()):
        if sid in rdata['players']:
            del rdata['players'][sid]
            emit('room_update', rdata, room=room)