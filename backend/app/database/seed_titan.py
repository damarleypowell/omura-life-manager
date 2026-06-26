"""
Titan Track seed data — loads the research-grounded roadmap (TITAN_TRACK_SPEC
§6 module library + §7 sequencing) into LearningTrack / LearningModule.

Idempotent: ``seed_titan(db)`` is a no-op if tracks already exist, so it is
safe to call on every startup. Prerequisites are wired by phase_code after all
modules are inserted, and the first module of each now-tier track is unlocked
to 'available' so the system has somewhere to start.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.database.models import LearningTrack, LearningModule, RoadmapSnapshot


# (code, name, description, target_tier, cadence, color, order)
TRACKS = [
    ("A", "Skill & Technical Development",
     "Deliberate-practice loops, retrieval + spacing, ship-real-artifact gates, and a domain-depth ledger — the founder-success predictor.",
     "now", "phase_gated", "#3B82F6", 1),
    ("B", "Decision-Making & Strategic Thinking",
     "Calibrated forecasting, base-rate discipline, process-vs-outcome journaling, survivorship audits, ruin-avoidance.",
     "now", "standing", "#8B5CF6", 2),
    ("C", "Leadership & Presence",
     "Prestige-path influence, warmth + competence, pitch mechanics, real-rep after-action review, and durable influence.",
     "now", "phase_gated", "#EC4899", 3),
    ("D", "Discipline Systems",
     "Habit architecture, perseverance-of-effort tracking, realistic timelines, burnout-vs-depression literacy.",
     "now", "phase_gated", "#22C55E", 4),
    ("E", "Stress & Physical Resilience",
     "Sleep protection (#1 lever), paced breathing, boxing framed honestly, graded stress-exposure reps.",
     "now", "standing", "#F59E0B", 5),
    ("HORIZON", "Systems & Power Literacy",
     "Long-horizon historical / economic case studies — reviewed quarterly, never in the daily flow. Every case ships with its failure twin.",
     "horizon", "quarterly", "#71717A", 6),
]


# Each module: dict with track code + sequencing + research metadata.
# prereq_codes are phase_codes within the SAME plan, resolved after insert.
MODULES = [
    # ── Track A — Skill & Technical Development (18-month sequence) ──
    dict(track="A", phase="A1", week=1, title="Python/SQL fundamentals",
         description="Variables, control flow, functions, basic data structures, SQL queries (Codecademy NLP path).",
         basis="Rowland 2014; Yang 2021; Pan & Rickard 2018 (retrieval + spacing)",
         conf="strong", note="STRONG: retrieval practice + spacing are among the most replicated findings in learning science.",
         fmt="course", prereqs=[], artifact="A working script that processes real IronLogic client data"),
    dict(track="A", phase="A2", week=9, title="NLP fundamentals for agents",
         description="NLP applied directly to chatbot / voice-agent work — narrow deliberate-practice loops with immediate feedback.",
         basis="Macnamara 2014/2016 (deliberate practice — early-stage power)",
         conf="strong", note="STRONG early-stage: practice strongly separates beginner→intermediate; it barely differentiates elites.",
         fmt="course", prereqs=["A1"], artifact="A new IronLogic client feature shipped (not a toy exercise)"),
    dict(track="A", phase="A3", week=17, title="ML fundamentals, applied",
         description="DeepLearning.AI specialization (first course) — each module ends in a deployed artifact, because near-transfer needs application.",
         basis="near-transfer / recognition-bottleneck research (Corral & Kurtz 2025)",
         conf="strong", note="STRONG: applied near-transfer requires shipping a real thing, not passive study.",
         fmt="mixed", prereqs=["A2"], artifact="One applied ML component integrated into Gotham Financial (e.g. a screener heuristic)"),
    dict(track="A", phase="A4", week=25, title="ML applied deeper",
         description="One full specialization, paced against the actual Gotham roadmap, not theory-first.",
         basis="Azoulay, Jones, Kim & Miranda 2020 (domain depth predicts founder success)",
         conf="strong", note="STRONG: specific industry experience — not age — is the strongest predictor of founder success.",
         fmt="mixed", prereqs=["A3"], artifact="A Gotham feature in production that uses what was learned"),
    dict(track="A", phase="A5", week=37, title="Direction chosen by company state",
         description="Specialization direction picked from where the companies actually are — left open deliberately.",
         basis="Sala & Gobet; Corral & Kurtz 2025 (far transfer is built, never assumed)",
         conf="strong", note="STRONG: skills are domain-specific; cross-domain benefit must be built with explicit bridges.",
         fmt="dynamic_challenge", prereqs=["A4"], artifact="Defined once reached, not pre-committed now"),
    dict(track="A", phase="A6", week=53, title="Deepen direction + optional credential",
         description="Deepen the A5 direction; consider a formal credential only if it serves a real pricing/positioning goal.",
         basis="Ritchie & Tucker-Drob 2018 (education as durable measured-ability gain)",
         conf="strong", note="STRONG: sustained structured learning durably raises measured cognitive performance.",
         fmt="mixed", prereqs=["A5"], artifact="A shipped capstone feature OR a passed certification tied to a business outcome"),

    # ── Track B — Decision-Making (standing practice, week 1 onward) ──
    dict(track="B", phase="B1", week=None, title="Probabilistic-judgment training",
         description="Forecast real business questions, assign probabilities, keep score, compute your own Brier score over time.",
         basis="Tetlock/Mellers — Good Judgment Project",
         conf="strong", note="STRONG that the practices are trainable; MODERATE on the size of the pure-training effect.",
         fmt="dynamic_challenge", prereqs=[], artifact="A running Brier score over 4+ weeks of logged forecasts"),
    dict(track="B", phase="B2", week=None, title="Base-rate discipline",
         description="Before any big call, find the outside-view base rate first (deal close rates, churn, conversion).",
         basis="Tetlock; Kahneman (outside view)",
         conf="strong", note="STRONG: starting from the outside-view base rate consistently beats inside-view intuition.",
         fmt="course", prereqs=[], artifact="A decision where you wrote the base rate before deciding"),
    dict(track="B", phase="B3", week=None, title="Decision journal (process vs outcome)",
         description="Grade the reasoning separately from the result — outcomes are noisy.",
         basis="luck-vs-skill literature; Mauboussin",
         conf="strong", note="STRONG (structure): judging process over outcome is sound decision hygiene.",
         fmt="course", prereqs=[], artifact="5+ journaled decisions with process graded apart from outcome"),
    dict(track="B", phase="B4", week=None, title="Survivorship-bias audit",
         description="On every piece of business advice consumed: where are the people who did this and failed?",
         basis="Denrell; startup-prediction literature",
         conf="strong", note="STRONG (method): correcting for invisible failures is a robust analytical habit.",
         fmt="case_study", prereqs=["B3"], artifact="A teardown of one popular piece of advice, failures included"),
    dict(track="B", phase="B5", week=None, title="Ruin-avoidance / variance literacy",
         description="Structure bets to be cheap and reversible; never bet the company; maximize the number of shots.",
         basis="Pluchino et al. 2018 (agent-based model); Taleb/Mauboussin",
         conf="theoretical", note="THEORETICAL (model) / STRONG (structural logic): the simulation illustrates a real statistical structure, not proof about the economy.",
         fmt="course", prereqs=["B4"], artifact="A bet restructured to be cheap + reversible"),

    # ── Track C — Leadership & Presence (18-month sequence) ──
    dict(track="C", phase="C1", week=1, title="Prestige-path fundamentals + dominance teardown",
         description="Lead with demonstrated competence + freely shared expertise. Includes the dominance/'alpha' teardown — taught directly, sourced, not avoided.",
         basis="Cheng, Tracy, Foulsham, Kingstone & Henrich 2013; McClanahan 2022",
         conf="strong", note="STRONG: prestige (competence + generosity) is the durable path; dominance costs liking + trust and decays without enforcement.",
         fmt="course", prereqs=[], artifact="Can articulate, unprompted, why dominance signaling costs trust over time"),
    dict(track="C", phase="C2", week=7, title="Vocal / rhetoric mechanics",
         description="Structure, vocal pacing, pause, clear short lines, audience-reading — drilled on real reps (every client/cold call).",
         basis="rhetoric skill-acquisition literature; Keating et al. 2020",
         conf="moderate", note="MODERATE: directionally safe (practice + feedback improves speaking) but effect magnitudes are softly quantified.",
         fmt="dynamic_challenge", prereqs=["C1"], artifact="A recorded pitch self-reviewed against the rubric"),
    dict(track="C", phase="C3", week=17, title="After-action review becomes automatic",
         description="Auto-pulled from real Lead/Communication data — clarity under pressure, naming the ask, where control got handed away, silence tolerance.",
         basis="general feedback-loop research",
         conf="strong", note="STRONG (mechanism): structured after-action review on real reps is a reliable improvement loop.",
         fmt="dynamic_challenge", prereqs=["C2"], artifact="10+ logged reps with reflections, not just transcripts"),
    dict(track="C", phase="C4", week=27, title="Durable influence",
         description="Track whether specific clients/contacts stay engaged over months — trust, consistency, individualized consideration — not whether a single pitch landed.",
         basis="transformational-leadership meta-analyses",
         conf="moderate", note="MODERATE (correlational) / STRONG (conceptual distinction): single-room charisma and multi-year followership are different constructs.",
         fmt="course", prereqs=["C3"], artifact="A real client relationship lasting 6+ months, with notes on what sustained it"),
    dict(track="C", phase="C5", week=53, title="Holding a room over time",
         description="Leading a recurring meeting/session, not a single pitch — quarterly-paced, the slowest-building skill in the track.",
         basis="transformational-leadership meta-analyses",
         conf="moderate", note="MODERATE: durable leadership evidence is mostly correlational; the structural point is sound.",
         fmt="dynamic_challenge", prereqs=["C4"], artifact="One real instance of leading a recurring group session for a full quarter"),

    # ── Track D — Discipline Systems (front-loaded, then maintenance) ──
    dict(track="D", phase="D1", week=1, title="Habit architecture setup",
         description="One stable cue, consistent timing (morning), smallest viable version, self-selected, positive affect engineered in.",
         basis="Singh et al. 2024 (systematic review, 2,601 participants); Kaushal & Rhodes 2015",
         conf="strong", note="STRONG (<6 months): median time-to-automaticity ~59-66 days; don't expect it done at week 3.",
         fmt="course", prereqs=[], artifact="Streak survives a full 9 weeks without a reset"),
    dict(track="D", phase="D2", week=10, title="Perseverance-of-effort tracking",
         description="Show up, finish, consistent effort — the primary discipline metric — explicitly decoupled from 'never change your goal'.",
         basis="Credé, Tynan & Harms 2017",
         conf="strong", note="STRONG (grit ≈ conscientiousness) / MODERATE (sub-facet): only perseverance-of-effort carries real weight.",
         fmt="course", prereqs=["D1"], artifact="A self-review showing consistent effort logged through a bad week"),
    dict(track="D", phase="D3", week=None, title="Quarterly durability review",
         description="Recurring durability check — flagged THEORETICAL: a hedge against the thin >6-month evidence, not a proven mechanism.",
         basis="gap in habit-durability literature",
         conf="theoretical", note="THEORETICAL: almost no research tracks habit survival past 12-18 months; this review is a hedge.",
         fmt="course", prereqs=["D2"], artifact=None),
    dict(track="D", phase="D-LIT", week=None, title="Burnout-vs-depression literacy",
         description="Burnout responds to rest; depression persists after the workload drops. Protective levers: sleep, real social connection, early help-seeking.",
         basis="Freeman et al. 2019 (self-report caveats noted)",
         conf="moderate", note="MODERATE: direction (elevated founder risk) is credible; exact percentages are soft self-report.",
         fmt="course", prereqs=[], artifact="Can distinguish burnout from depression and name the protective levers"),

    # ── Track E — Stress & Physical Resilience (parallel, week 1 onward) ──
    dict(track="E", phase="E1", week=None, title="Sleep protection (#1 cognitive lever)",
         description="A protected sleep window, tracked, non-negotiable before high-stakes work (pitches, big builds).",
         basis="Lowe et al. 2017 + 70-study meta-analyses",
         conf="strong", note="STRONG: protecting sleep is the single best-evidenced cognitive intervention — and it's free.",
         fmt="course", prereqs=[], artifact="A tracked, protected sleep window held before a high-stakes day"),
    dict(track="E", phase="E2", week=None, title="Slow paced breathing (~6/min)",
         description="Before high-pressure moments. The active ingredient is the breathing, not a device.",
         basis="Goessl 2017; Lehrer 2020",
         conf="moderate", note="MODERATE / CONTESTED: mixed, partly self-report evidence; included because it's nearly free and low-risk.",
         fmt="course", prereqs=[], artifact="Paced breathing run before one real high-pressure moment"),
    dict(track="E", phase="E3", week=None, title="Boxing — framed honestly",
         description="Discipline, stress-physiology, mood, controlled arousal exposure — NOT framed as a cognitive enhancer.",
         basis="exercise-mood literature strong; combat-to-cognition link weak/observational",
         conf="moderate", note="MODERATE / weak: real benefits are fitness/mood/stress-physiology; the cognition transfer is a personal hypothesis to test.",
         fmt="course", prereqs=[], artifact="Boxing routine continued, reframed by the research"),
    dict(track="E", phase="E4", week=None, title="Graded stress-exposure reps",
         description="Timed mock Q&A, live-demo rehearsals, stepped up over time, before major pitches.",
         basis="stress inoculation (Meichenbaum)",
         conf="moderate", note="MODERATE: reasonable short-to-medium-term evidence; long-term durability is less established.",
         fmt="dynamic_challenge", prereqs=[], artifact="A stepped-up mock Q&A run before a real pitch"),

    # ── Horizon Tier — Systems & Power Literacy (quarterly, failure twins) ──
    dict(track="HORIZON", phase="H1", week=None, title="Economic-structure literacy",
         description="Power laws, compounding, heavy-tailed outcomes, base rates of extreme success.",
         basis="Pluchino; Mauboussin; Pareto",
         conf="theoretical", note="THEORETICAL / STRONG (structure): the model is a simulation, but the heavy-tailed statistical structure is real.",
         fmt="case_study", prereqs=[], artifact=None, failure_twin=False),
    dict(track="HORIZON", phase="H2", week=None, title="Historical strategy case studies",
         description="Each case paired with its failure twin (someone who did the same and failed) and the luck/timing factors named explicitly.",
         basis="survivorship-bias methodology",
         conf="strong", note="STRONG (method): the failure twin is mandatory — no highlight reels.",
         fmt="case_study", prereqs=[], artifact=None, failure_twin=True),
    dict(track="HORIZON", phase="H3", week=None, title="Heritability & individual-ceiling literacy",
         description="Why population statistics say nothing about your personal cap, and why gene-environment leverage is highest right now at 18.",
         basis="Ritchie & Tucker-Drob 2018; behavioral-genetics methodology",
         conf="strong", note="STRONG (corrections): heritability is a population-variance statistic — not immutability, not a personal ceiling.",
         fmt="case_study", prereqs=[], artifact=None, failure_twin=False),
]

COMPASS_NOTE = (
    "Private city / eventual nation — the long-term compass bearing. Stored here, "
    "not as a module: no quiz, reviewed yearly, not quarterly."
)


def seed_titan(db: Session) -> dict:
    """Insert tracks + modules if the roadmap is empty. Idempotent: a no-op once
    seeded, so it is safe to call on every startup. Returns a small report."""
    existing = db.query(LearningTrack).count()
    if existing:
        return {"seeded": False, "reason": "already_seeded", "tracks": existing}

    # Insert tracks
    track_by_code: dict = {}
    for code, name, desc, tier, cadence, color, order in TRACKS:
        t = db.query(LearningTrack).filter(LearningTrack.code == code).first()
        if not t:
            t = LearningTrack(
                code=code, name=name, description=desc, target_tier=tier,
                cadence=cadence, color_theme=color, order_index=order,
            )
            db.add(t)
            db.flush()
        track_by_code[code] = t

    # Insert modules (first pass — no prereqs yet)
    module_by_phase: dict = {}
    order_counter: dict = {}
    for spec in MODULES:
        code = spec["track"]
        track = track_by_code[code]
        if db.query(LearningModule).filter(
            LearningModule.track_id == track.id,
            LearningModule.phase_code == spec["phase"],
        ).first():
            continue
        order_counter[code] = order_counter.get(code, 0) + 1
        m = LearningModule(
            track_id=track.id,
            title=spec["title"],
            description=spec["description"],
            tier=track.target_tier,
            format=spec.get("fmt", "course"),
            research_basis=spec["basis"],
            confidence_level=spec["conf"],
            confidence_note=spec.get("note"),
            prerequisite_ids=[],
            order_index=order_counter[code],
            status="locked",
            requires_failure_twin=bool(spec.get("failure_twin", False)),
            week_number=spec.get("week"),
            phase_code=spec["phase"],
            culminating_artifact=spec.get("artifact"),
            extra_data={"prereq_codes": spec.get("prereqs", [])},
        )
        db.add(m)
        db.flush()
        module_by_phase[(code, spec["phase"])] = m

    # Second pass — resolve prerequisite phase_codes to module ids
    for (code, phase), m in module_by_phase.items():
        prereq_codes = (m.extra_data or {}).get("prereq_codes", [])
        prereq_ids = [
            module_by_phase[(code, pc)].id
            for pc in prereq_codes
            if (code, pc) in module_by_phase
        ]
        m.prerequisite_ids = prereq_ids
        # Unlock entry points: any module with no prerequisites becomes available.
        if not prereq_ids:
            m.status = "available"

    # Seed the initial roadmap snapshot with the long-term compass note.
    if not db.query(RoadmapSnapshot).first():
        db.add(RoadmapSnapshot(
            version=1, full_roadmap_json={}, change_note="Initial seeded roadmap",
            compass_note=COMPASS_NOTE,
        ))

    db.commit()
    return {
        "seeded": True,
        "tracks": len(track_by_code),
        "modules": len(module_by_phase),
    }


if __name__ == "__main__":  # manual one-shot: python -m backend.app.database.seed_titan
    from backend.app.database.session import SessionLocal
    _db = SessionLocal()
    try:
        print(seed_titan(_db))
    finally:
        _db.close()
