"""Tiny macOS menu-bar toggle (rumps). No talk-back, no UI beyond on/off/mute.

    🎙  capturing        ⏸  session off        🔇  muted

It only flips the shared state file; the launchd daemon does the work.
"""

from . import state as state_mod
from .config import load_config


def main() -> None:
    import rumps

    cfg = load_config()

    class VoiceInboxApp(rumps.App):
        def __init__(self):
            super().__init__("🎙", quit_button="Quit menu bar (daemon keeps running)")
            self.listening_item = rumps.MenuItem("Office session on", callback=self.toggle_listening)
            self.mute_item = rumps.MenuItem("Mute mic", callback=self.toggle_mute)
            self.open_item = rumps.MenuItem("Open today's local inbox", callback=self.open_today)
            self.menu = [self.listening_item, self.mute_item, None, self.open_item]
            self.refresh(None)
            rumps.Timer(self.refresh, 2).start()

        def refresh(self, _):
            st = state_mod.read_state(cfg.state_file)
            self.listening_item.state = 1 if st["listening"] else 0
            self.mute_item.state = 1 if st["muted"] else 0
            if not st["listening"]:
                self.title = "⏸"
            elif st["muted"]:
                self.title = "🔇"
            else:
                self.title = "🎙"

        def toggle_listening(self, _):
            st = state_mod.read_state(cfg.state_file)
            state_mod.write_state(cfg.state_file, listening=not st["listening"])
            self.refresh(None)

        def toggle_mute(self, _):
            st = state_mod.read_state(cfg.state_file)
            state_mod.write_state(cfg.state_file, muted=not st["muted"])
            self.refresh(None)

        def open_today(self, _):
            import subprocess

            from .inbox import day_key, local_now, local_path

            path = local_path(cfg, day_key(cfg, local_now(cfg)))
            if path.is_file():
                subprocess.run(["open", str(path)], check=False)
            else:
                rumps.notification("Office Voice Inbox", "", "Nothing captured today yet.")

    VoiceInboxApp().run()


if __name__ == "__main__":
    main()
