import time
import random
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models.game import GameRecord, ArcadeLeaderboard
from app.services.arcade_content_engine import ArcadeContentEngine
from app.services.ai_typist_engine import AITypistSimulator

ARCADE_ROOMS = {} # room_code -> room_state
ARCADE_QUEUES = {} # game_mode -> [{'sid', 'name', 'user_id', 'wpm'}]
ARCADE_SID_MAP = {} # sid -> room_code

def register_arcade_socket_events():
    @socketio.on('arcade_init')
    def handle_arcade_init(data):
        game_mode = data.get('game_mode', 'falling_words')
        play_mode = data.get('play_mode', 'solo_ai') # 'solo_ai', '1v1_private', '1v1_matchmake', 'multiplayer'
        difficulty = data.get('difficulty', 'intermediate')
        ai_level = data.get('ai_level', 'intermediate')
        custom_code = (data.get('room_code') or '').strip().upper()
        player_name = data.get('player_name', 'Pilot')
        sid = request.sid

        # 1. Clean prior sessions
        cleanup_arcade_socket(sid)

        # 2. Solo with AI Opponent
        if play_mode == 'solo_ai':
            room_code = f"AI-{sid[:6].upper()}"
            content = ArcadeContentEngine.get_content_batch(game_mode, difficulty, count=40)
            
            ARCADE_ROOMS[room_code] = {
                'game_mode': game_mode,
                'play_mode': 'solo_ai',
                'difficulty': difficulty,
                'status': 'active',
                'start_time': time.time(),
                'content': content,
                'players': {
                    sid: {'name': player_name, 'score': 0, 'progress': 0, 'wpm': 0, 'finished': False, 'is_ai': False},
                    'ai_bot': {'name': f"CyberTypist ({ai_level.title()})", 'score': 0, 'progress': 0, 'wpm': 0, 'finished': False, 'is_ai': True}
                },
                'ai_sim': AITypistSimulator(level=ai_level)
            }
            ARCADE_SID_MAP[sid] = room_code
            join_room(room_code)
            emit('arcade_session_started', {'room_code': room_code, 'content': content, 'is_solo': True})
            return

        # 3. Private 1v1 Room Creation or Join
        if play_mode in ['1v1_private', 'multiplayer']:
            if custom_code and custom_code in ARCADE_ROOMS:
                room = ARCADE_ROOMS[custom_code]
                if room['status'] != 'lobby':
                    emit('arcade_error', {'message': 'This room has already started.'})
                    return
                if len(room['players']) >= room['max_players']:
                    emit('arcade_error', {'message': 'Room is full.'})
                    return
                
                room['players'][sid] = {'name': player_name, 'score': 0, 'progress': 0, 'wpm': 0, 'ready': False, 'finished': False, 'is_ai': False}
                ARCADE_SID_MAP[sid] = custom_code
                join_room(custom_code)
                emit('arcade_room_joined', {'room_code': custom_code, 'players': room['players'], 'is_host': False})
                emit('arcade_lobby_update', {'players': room['players']}, room=custom_code)
            else:
                new_code = custom_code or f"ARC-{random.randint(1000, 9999)}"
                content = ArcadeContentEngine.get_content_batch(game_mode, difficulty, count=40)
                max_p = 2 if play_mode == '1v1_private' else int(data.get('max_players', 4))
                
                ARCADE_ROOMS[new_code] = {
                    'game_mode': game_mode,
                    'play_mode': play_mode,
                    'difficulty': difficulty,
                    'status': 'lobby',
                    'host_sid': sid,
                    'max_players': max_p,
                    'content': content,
                    'players': {
                        sid: {'name': player_name, 'score': 0, 'progress': 0, 'wpm': 0, 'ready': True, 'finished': False, 'is_ai': False}
                    }
                }
                ARCADE_SID_MAP[sid] = new_code
                join_room(new_code)
                emit('arcade_room_joined', {'room_code': new_code, 'players': ARCADE_ROOMS[new_code]['players'], 'is_host': True})

    @socketio.on('arcade_ai_tick')
    def handle_ai_tick(data):
        sid = request.sid
        room_code = ARCADE_SID_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if room.get('play_mode') != 'solo_ai' or not room.get('ai_sim'):
            return
        
        delta = float(data.get('delta', 0.2))
        ai_data = room['players']['ai_bot']
        new_prog, cur_wpm = room['ai_sim'].get_progress_step(delta, ai_data['progress'], 250)
        
        ai_data['progress'] = new_prog
        ai_data['wpm'] = cur_wpm
        ai_data['score'] = int(new_prog * 12)
        if new_prog >= 100:
            ai_data['finished'] = True
            
        emit('arcade_sync_tick', {'players': room['players']}, room=room_code)

    @socketio.on('arcade_player_progress')
    def handle_player_progress(data):
        sid = request.sid
        room_code = ARCADE_SID_MAP.get(sid)
        if not room_code or room_code not in ARCADE_ROOMS:
            return
        room = ARCADE_ROOMS[room_code]
        if sid not in room['players']:
            return

        p = room['players'][sid]
        p['progress'] = float(data.get('progress', 0))
        p['score'] = int(data.get('score', 0))
        p['wpm'] = float(data.get('wpm', 0))
        p['accuracy'] = float(data.get('accuracy', 100))
        p['combo'] = int(data.get('combo', 0))
        
        if p['progress'] >= 100 and not p['finished']:
            p['finished'] = True
            p['finish_time'] = round(time.time() - room.get('start_time', time.time()), 2)
            
        emit('arcade_sync_tick', {'players': room['players']}, room=room_code)

    @socketio.on('arcade_disconnect')
    def handle_arcade_disconnect():
        cleanup_arcade_socket(request.sid)

def cleanup_arcade_socket(sid):
    room_code = ARCADE_SID_MAP.pop(sid, None)
    if room_code and room_code in ARCADE_ROOMS:
        room = ARCADE_ROOMS[room_code]
        leave_room(room_code, sid=sid)
        if sid in room['players']:
            del room['players'][sid]
        if not room['players'] or (len(room['players']) == 1 and 'ai_bot' in room['players']):
            del ARCADE_ROOMS[room_code]
        else:
            emit('arcade_lobby_update', {'players': room['players']}, room=room_code)