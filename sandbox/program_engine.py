import json, os, sqlite3, time
from typing import Dict, Any, List

SukoonAI_DISCLAIMER_EN = (
  "Disclaimer: SukoonAI is an educational wellness tool and not a substitute "
  "for professional medical or mental health advice."
)
SukoonAI_DISCLAIMER_UR = (
  "Wazahat: SukoonAI taleemi wellness tool hai. Yeh kisi tabibi ya zehni sehat "
  "ke mahir mashwaray ka badal nahi."
)

CRISIS_KEYWORDS = {"suicide", "kill myself", "self harm", "end my life", "انتحار", "قتل", "zakhmi", "harm myself"}

def is_crisis(text: str) -> bool:
    if not text: 
        return False
    t = text.lower()
    return any(k in t for k in CRISIS_KEYWORDS)


class ProgramRegistry:
    """Loads program JSON files from a folder (e.g., ./programs)."""
    def __init__(self, folder="programs"):
        self.folder = folder
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self):
        self.cache.clear()
        if not os.path.isdir(self.folder): return
        for fn in os.listdir(self.folder):
            if fn.endswith(".json"):
                with open(os.path.join(self.folder, fn), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pid = data.get("id") or os.path.splitext(fn)[0]
                    self.cache[pid] = data

    def list_programs(self) -> List[Dict[str, Any]]:
        return [{"id": p["id"], "name": p["name"], "duration_days": p.get("duration_days", len(p.get("steps", [])))} for p in self.cache.values()]

    def get(self, program_id: str) -> Dict[str, Any]:
        return self.cache[program_id]


class ProgramEngine:
    def __init__(self, db_path="sehat.db", programs_folder="programs"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_db()
        self.registry = ProgramRegistry(programs_folder)

    def _init_db(self):
        cur = self.db.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
          user_id TEXT PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS enrollments (
          user_id TEXT NOT NULL, program_id TEXT NOT NULL,
          current_step_index INTEGER NOT NULL DEFAULT 0,
          started_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          completed INTEGER DEFAULT 0,
          PRIMARY KEY (user_id, program_id))""")
        self.db.commit()

    def ensure_user(self, user_id: str):
        cur = self.db.cursor()
        cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
        self.db.commit()

    def enroll(self, user_id: str, program_id: str):
        self.ensure_user(user_id)
        cur = self.db.cursor()
        cur.execute("""INSERT OR IGNORE INTO enrollments(user_id, program_id)
                       VALUES (?, ?)""", (user_id, program_id))
        self.db.commit()

    def next_step(self, user_id: str, program_id: str) -> str:
        prog = self.registry.get(program_id)
        steps = prog.get("steps", [])
        cur = self.db.cursor()
        row = cur.execute("""SELECT current_step_index, completed
                             FROM enrollments WHERE user_id=? AND program_id=?""",
                          (user_id, program_id)).fetchone()
        if not row:
            self.enroll(user_id, program_id)
            idx, completed = 0, 0
        else:
            idx, completed = row["current_step_index"], row["completed"]

        if completed or idx >= len(steps):
            return self._format_done(prog)

        step = steps[idx]
        # advance progress
        cur.execute("""UPDATE enrollments
                       SET current_step_index=?, updated_at=?, completed=?
                       WHERE user_id=? AND program_id=?""",
                    (idx + 1, time.strftime("%Y-%m-%d %H:%M:%S"),
                     1 if (idx + 1) >= len(steps) else 0, user_id, program_id))
        self.db.commit()

        return self._format_step(step, prog)

    def reset(self, user_id: str, program_id: str):
        cur = self.db.cursor()
        cur.execute("""UPDATE enrollments SET current_step_index=0, completed=0,
                       updated_at=? WHERE user_id=? AND program_id=?""",
                    (time.strftime("%Y-%m-%d %H:%M:%S"), user_id, program_id))
        self.db.commit()

    # ---- Formatting (SukoonAI style: Answer → Source → Disclaimer) ----
    def _format_step(self, step: Dict[str, Any], prog: Dict[str, Any]) -> str:
        src = prog.get("id", "program.json")
        en = step.get("en", "No English text.")
        ur = step.get("ur", "Koi Urdu matn nahi mila.")
        src_line = f"📖 Source: {src}"
        disc = f"⚠️ {SukoonAI_DISCLAIMER_EN}\n⚠️ {SukoonAI_DISCLAIMER_UR}"
        return f"{en}\n\n{ur}\n\n{src_line}\n{disc}"

    def _format_done(self, prog: Dict[str, Any]) -> str:
        src = prog.get("id", "program.json")
        en = "🎉 Program complete! You can repeat or explore another program."
        ur = "🎉 Program mukammal ho gaya! Aap dobara shuru kar sakte hain ya koi naya program koshish karein."
        return self._format_step({"en": en, "ur": ur}, prog)
