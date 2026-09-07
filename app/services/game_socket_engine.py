import time
import random
from flask import request
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models.game import GameRecord, ArcadeLeaderboard
from app.services.arcade_content_engine import ArcadeContentEngine
from app.services.ai_typist_engine import AITypistSimulator

ARCADE_ROOMS = {}
ARCADE_SOCKET_MAP = {}

def register_arcade_socket_events():
    @socketio.on('arcade_room_create')
    def on_arcade_create(data):
        sid = request.sid
        game_slug = data.get('game_slug')
        mode = data.get('play_mode', 'solo_ai')
        difficulty = data.get('difficulty', 'moderate')
        objective_type = data.get('objective_type', 'timed')
        objective_val = data.get('objective_val', 60)
        blind_mode = bool(data.get('blind_mode', False))
        backspace_allowed = bool(data.get('backspace_allowed', True))
        player_name = data.get('player_name', 'Pilot')
        custom_code = (data.get('room_code') or '').strip().upper()

        cleanup_socket(sid)

        room_code = custom_code or f"G-{random.randint(1000, 9999)}"
        content = ArcadeContentEngine.get_content_batch(game_slug, difficulty, count=40, extra_filters=data)

        ARCADE_ROOMS[room_code] = {
            'room_code': room_code,
            'game_slug': game_slug,
            'play_mode': mode,
            'difficulty': difficulty,
            'objective_type': objective_type,
            'objective_val': objective_val,
            'blind_mode': blind_mode,
            'backspace_allowed': backspace_allowed,
            'content': content,
            'status': 'lobby' if mode != 'solo_ai' else 'racing',
            'host_sid': sid,
            'created_at': time.time(),
            'start_time': time.time(),
            'players': {
                sid: {
                    'name': player_name,
                    'progress': 0.0,
                    'score': 0,
                    'wpm': 0,
                    'accuracy': 100,
                    'errors': 0,
                    'finished': False,
                    'ready': True,
                    'is_ai': False
                }
            }
        }

        if mode == 'solo_ai':
            ARCADE_ROOMS[room_code]['players']['ai_bot'] = {
                'name': f"CyberBot ({difficulty.title()})",
                'progress': 0.0,
                'score': 0,
                'wpm': 0,
                'accuracy': 98,
                'errors': 0,
                'finished': False,
                'ready': True,
                'is_ai': True
            }
            ARCADE_ROOMS[room_code]['ai_sim'] = AITypistSimulator(difficulty=difficulty)

        ARCADE_SOCKET_MAP[sid] = room_code
        join_room(room_code)
        emit('arcade_room_ready', ARCADE_ROOMS[room_code])

    @socketio.on('arcade_room_join')
    def on_arcade_join(data):
        sid = request.sid
        room_code = (data.get('room_code') or '').strip().upper()
        player_name = data.get('player_name', 'Pilot')

        if room_code not in ARCADE_ROOMS:
            emit('arcade_error', {'message': f"Room {room_code} not found."})
            return

        room = ARCADE_ROOMS[room_code]
        if room['status'] != 'lobby':
            emit('arcade_error', {'message': 'Game already in progress.'})
            return

        if len(room['players']) >= 4:
            emit('arcade_error', {'message': 'Room full.'})
            return

        cleanup_socket(sid)

        room['players'][sid] = {
            'name': player_name,
            'progress': 0.0,
            'score': 0,
            'wpm': 0,
            'accuracy': 100,
            'errors': 0,
            'finished': False,
            'ready': False,
            'is_ai': False
        }

        ARCADE_SOCKET_MAP[sid] = room_code
        join_room(room_code)
        emit('arcade_room_ready', room)
        emit('arcade_roster_update', {'players': room['players']}, room=room_code)

    @socketio.on('arcade_toggle_ready')
    def on_arcade_ready():
        sid = request.sid
        room_code = ARCADE_SOCKET_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if sid in room['players']:
            room['players'][sid]['ready'] = not room['players'][sid]['ready']
            emit('arcade_roster_update', {'players': room['players']}, room=room_code)

    @socketio.on('arcade_start_countdown')
    def on_arcade_start():
        sid = request.sid
        room_code = ARCADE_SOCKET_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if room['host_sid'] != sid:
            return
        room['status'] = 'countdown'
        emit('arcade_countdown_trigger', {'duration': 3}, room=room_code)

    @socketio.on('arcade_progress_sync')
    def on_progress_sync(data):
        sid = request.sid
        room_code = ARCADE_SOCKET_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if sid not in room['players']:
            return

        p = room['players'][sid]
        p['progress'] = float(data.get('progress', 0.0))
        p['score'] = int(data.get('score', 0))
        p['wpm'] = float(data.get('wpm', 0))
        p['accuracy'] = float(data.get('accuracy', 100))
        p['errors'] = int(data.get('errors', 0))
        if data.get('finished'):
            p['finished'] = True

        emit('arcade_live_telemetry', {'players': room['players']}, room=room_code)

    @socketio.on('arcade_ai_tick')
    def on_ai_tick(data):
        sid = request.sid
        room_code = ARCADE_SOCKET_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if 'ai_sim' not in room or 'ai_bot' not in room['players']:
            return

        delta = float(data.get('delta', 0.25))
        total_len = int(data.get('total_chars', 300))
        prog, wpm = room['ai_sim'].step(delta, total_len)

        bot = room['players']['ai_bot']
        bot['progress'] = prog
        bot['wpm'] = wpm
        bot['score'] = int(prog * 15)
        if prog >= 100:
            bot['finished'] = True

        emit('arcade_live_telemetry', {'players': room['players']}, room=room_code)

def cleanup_socket(sid):
    room_code = ARCADE_SOCKET_MAP.pop(sid, None)
    if room_code and room_code in ARCADE_ROOMS:
        room = ARCADE_ROOMS[room_code]
        leave_room(room_code, sid=sid)
        if sid in room['players']:
            del room['players'][sid]
        if not room['players'] or (len(room['players']) == 1 and 'ai_bot' in room['players']):
            del ARCADE_ROOMS[room_code]
        else:
            emit('arcade_roster_update', {'players': room['players']}, room=room_code)