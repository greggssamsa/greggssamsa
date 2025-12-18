# =============================
# DOZ HESAPLAYICI – ANDROID APK (KIVY)
# TEK DOSYA – HAZIR
# =============================

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import difflib
import math

# =============================
# HELPERS
# =============================

def parse_frequency_to_doses_per_day(freq: str) -> Optional[float]:
    f = freq.strip().lower().replace(" ", "")
    if f.startswith("günde"):
        num = "".join(ch for ch in f if ch.isdigit())
        return float(num) if num else None
    if f in ("od", "q24h"):
        return 1.0
    if f.startswith("q") and f.endswith("h"):
        num = f[1:-1]
        if num.isdigit():
            hours = int(num)
            if hours > 0:
                return 24.0 / hours
    return None

def mosteller_bsa_m2(weight_kg: float, height_cm: float) -> float:
    return math.sqrt((height_cm * weight_kg) / 3600.0)

def normalize_text(s: str) -> str:
    s = s.strip().lower()
    tr = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})
    s = s.translate(tr)
    s = " ".join(s.split())
    return s

# =============================
# CORE MODELS
# =============================

@dataclass
class DoseRule:
    indication: str
    route: str
    frequency: str
    mg_per_kg_per_day: Optional[float] = None
    mg_per_kg_per_dose: Optional[float] = None
    mg_per_m2_per_day: Optional[float] = None
    mg_per_m2_per_dose: Optional[float] = None
    max_mg_per_day: Optional[float] = None
    max_mg_per_dose: Optional[float] = None
    notes: str = ""

    def doses_per_day(self) -> Optional[float]:
        return parse_frequency_to_doses_per_day(self.frequency)

    def needs_bsa(self) -> bool:
        return self.mg_per_m2_per_day is not None or self.mg_per_m2_per_dose is not None

    def describe(self) -> str:
        parts = []
        if self.mg_per_kg_per_day is not None:
            parts.append(f"{self.mg_per_kg_per_day} mg/kg/gün")
        if self.mg_per_kg_per_dose is not None:
            parts.append(f"{self.mg_per_kg_per_dose} mg/kg/doz")
        if self.mg_per_m2_per_day is not None:
            parts.append(f"{self.mg_per_m2_per_day} mg/m²/gün")
        return " / ".join(parts) + f", {self.route}, {self.frequency}"

class Drug:
    def __init__(self, name: str):
        self.name = name
        self.rules: List[DoseRule] = []

    def add_rule(self, rule: DoseRule):
        self.rules.append(rule)

    def rules_by_indication(self):
        d = {}
        for r in self.rules:
            d.setdefault(r.indication, []).append(r)
        return d

@dataclass
class Patient:
    weight_kg: float
    height_cm: Optional[float] = None

    def bsa_weight_only_m2(self):
        w = self.weight_kg
        return ((w * 4) + 7) / (w + 90)

# =============================
# CALC
# =============================

def calc_rule(r: DoseRule, pt: Patient) -> List[str]:
    out = []
    dpd = r.doses_per_day()
    if r.mg_per_kg_per_day:
        mg_day = r.mg_per_kg_per_day * pt.weight_kg
        mg_dose = mg_day / dpd if dpd else mg_day
        out.append(f"→ {mg_dose:.0f} mg/doz")
        out.append(f"→ {mg_day:.0f} mg/gün")
    return out

# =============================
# REGISTRY
# =============================

REGISTRY: Dict[str, Drug] = {}

def register(d: Drug):
    REGISTRY[d.name.lower()] = d

amp = Drug("Ampisilin Sulbaktam")
amp.add_rule(DoseRule("genel", "IV", "q6h", mg_per_kg_per_day=100))
amp.add_rule(DoseRule("genel", "IV", "q6h", mg_per_kg_per_day=200))
register(amp)

# =============================
# COMPUTE TEXT
# =============================

def compute_text(weight: float, drug_query: str) -> str:
    pt = Patient(weight)
    drug = REGISTRY.get(drug_query.lower())
    if not drug:
        return "İlaç bulunamadı."

    lines = []
    lines.append(f"İLAÇ: {drug.name}")
    lines.append(f"Kilo: {weight} kg")

    for ind, rules in drug.rules_by_indication().items():
        lines.append(f"\n{ind.upper()}:")
        for r in rules:
            lines.append("  " + r.describe())
            for x in calc_rule(r, pt):
                lines.append("   " + x)

    return "\n".join(lines)

# =============================
# KIVY UI
# =============================

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

class Root(BoxLayout):
    def __init__(self):
        super().__init__(orientation="vertical", padding=10, spacing=8)

        self.w = TextInput(hint_text="Kilo (kg)", input_filter="float", multiline=False)
        self.d = TextInput(hint_text="İlaç adı (ampisilin sulbaktam)", multiline=False)
        btn = Button(text="Hesapla")
        self.out = Label(text="", size_hint_y=None)
        self.out.bind(width=lambda *_: self._resize())

        btn.bind(on_press=self.calc)

        sc = ScrollView()
        sc.add_widget(self.out)

        for x in (self.w, self.d, btn, sc):
            self.add_widget(x)

    def _resize(self):
        self.out.text_size = (self.out.width, None)
        self.out.texture_update()
        self.out.height = max(self.out.texture_size[1], 300)

    def calc(self, *_):
        try:
            self.out.text = compute_text(float(self.w.text), self.d.text.strip())
        except Exception as e:
            self.out.text = str(e)

class DozApp(App):
    def build(self):
        return Root()

DozApp().run()
