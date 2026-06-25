import os
import re
import sqlite3
import subprocess
import configparser
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


class DemoExtension(Extension):
    def __init__(self):
        super(DemoExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def __init__(self):
        super(KeywordQueryEventListener, self).__init__()
        self.profiles = []

    def get_profiles_from_sqlite(self, config_folder):
        groups_dir = os.path.join(config_folder, 'Profile Groups')
        if not os.path.isdir(groups_dir):
            return None
        sqlite_files = [f for f in os.listdir(groups_dir) if f.endswith('.sqlite')]
        if not sqlite_files:
            return None
        try:
            conn = sqlite3.connect(os.path.join(groups_dir, sqlite_files[0]))
            cursor = conn.cursor()
            cursor.execute('SELECT name, path FROM Profiles ORDER BY id')
            profiles = [(row[0], row[1]) for row in cursor.fetchall()]
            conn.close()
            return profiles
        except Exception:
            return None

    def get_profiles_from_ini(self, config_folder):
        config = configparser.ConfigParser()
        config.read(os.path.join(config_folder, 'profiles.ini'))
        regex = r'^Profile.*$'
        return [
            (config[p]['Name'], config[p].get('Path', config[p]['Name']))
            for p in config.sections()
            if 'Name' in config[p] and re.search(regex, p, re.IGNORECASE)
        ]

    def get_profiles(self, config_folder):
        profiles = self.get_profiles_from_sqlite(config_folder)
        if profiles is not None:
            return profiles
        return self.get_profiles_from_ini(config_folder)

    def on_event(self, event, extension):
        query = event.get_argument()

        if not query or len(self.profiles) == 0:
            config_folder = os.path.expanduser(extension.preferences['librewolf_folder'])
            self.profiles = self.get_profiles(config_folder)

        profiles = self.profiles.copy()

        if query:
            query = query.strip().lower()
            profiles = [(name, path) for name, path in profiles if query in name.lower()]

        entries = []
        for name, path in profiles:
            entries.append(ExtensionResultItem(
                icon='images/icon.png',
                name=name,
                on_enter=ExtensionCustomAction({'name': name, 'path': path}, keep_app_open=False)
            ))

        entries.append(ExtensionResultItem(
            icon='images/icon.png',
            name='Profile Management',
            description='Start LibreWolf profile management tool',
            on_enter=ExtensionCustomAction('', keep_app_open=False)
        ))

        return RenderResultListAction(entries)


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()
        cmd = extension.preferences['librewolf_cmd']

        if isinstance(data, dict):
            config_folder = os.path.expanduser(extension.preferences['librewolf_folder'])
            profile_path = os.path.join(config_folder, data['path'])
            subprocess.Popen([cmd, '--profile', profile_path], start_new_session=True)
        else:
            subprocess.Popen([cmd, '-p', data], start_new_session=True)


if __name__ == '__main__':
    DemoExtension().run()
