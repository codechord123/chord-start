import json, os, uuid

class DataManager:
    def __init__(self):
        base = os.path.dirname(os.path.abspath(__file__))
        self._data_file = os.path.join(base, 'data.json')
        self._cfg_file  = os.path.join(base, 'config.json')
        self._events   = {}   # date_str → [event_dict, ...]
        self._teachers = []
        self._config   = {}
        self._load()

    # ── Load / Save ──────────────────────────────────────────────────────────
    def _load(self):
        try:
            with open(self._data_file, encoding='utf-8') as f:
                d = json.load(f)
            self._events   = d.get('events', {})
            self._teachers = d.get('teachers', [])
        except Exception:
            pass
        try:
            with open(self._cfg_file, encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception:
            pass

    def _save_data(self):
        with open(self._data_file, 'w', encoding='utf-8') as f:
            json.dump({'events': self._events, 'teachers': self._teachers},
                      f, ensure_ascii=False, indent=2)

    def _save_cfg(self):
        with open(self._cfg_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    # ── Config ───────────────────────────────────────────────────────────────
    def get_setting(self, key, default=None):
        return self._config.get(key, default)

    def set_setting(self, key, value):
        self._config[key] = value
        self._save_cfg()

    def is_setup_done(self):
        return bool(self._config.get('my_id'))

    # ── Teacher ──────────────────────────────────────────────────────────────
    def all_teachers(self):
        return list(self._teachers)

    def get_teacher(self, tid):
        return next((t for t in self._teachers if t['id'] == tid), None)

    def get_me(self):
        return self.get_teacher(self._config.get('my_id', ''))

    def save_teacher(self, teacher):
        for i, t in enumerate(self._teachers):
            if t['id'] == teacher['id']:
                self._teachers[i] = teacher
                self._save_data()
                return
        self._teachers.append(teacher)
        self._save_data()

    def setup_me(self, name, color):
        my_id = self._config.get('my_id') or uuid.uuid4().hex[:8]
        t = {'id': my_id, 'name': name, 'color': color}
        self.save_teacher(t)
        self._config['my_id'] = my_id
        self._save_cfg()
        return t

    # ── Events ───────────────────────────────────────────────────────────────
    def get_events(self, date_str):
        return list(self._events.get(date_str, []))

    def save_event(self, event):
        # Remove old entry (handles date change on edit)
        for v in self._events.values():
            for i, e in enumerate(v):
                if e['id'] == event['id']:
                    v.pop(i)
                    break
        key = event['date']
        self._events.setdefault(key, []).append(event)
        self._save_data()

    def delete_event(self, event_id):
        for v in self._events.values():
            for i, e in enumerate(v):
                if e['id'] == event_id:
                    v.pop(i)
                    break
        self._save_data()

    @staticmethod
    def new_id():
        return uuid.uuid4().hex[:8]
