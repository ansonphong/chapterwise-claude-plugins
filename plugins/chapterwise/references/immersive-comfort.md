# Immersive Comfort & Pacing

Thresholds, rhythm rules, and arc models for immersive work. Read alongside `immersive-effects.md`, which names the techniques these rules govern.

Two claims organize everything here:

1. **Awe cannot be sustained.** It spikes and resets. A show that tries to hold a peak produces fatigue, not wonder.
2. **Wide-field motion is the only thing in this medium that can make an audience physically ill.** It is worth budgeting like a resource.

---

## Evidence status

Immersive craft is a young field with a great deal of confident folklore. This document marks what is measured and what is consensus, because presenting the second as the first would be dishonest — and because knowing which is which tells you where to trust your own judgment.

| Tier | Meaning | How to treat it |
|---|---|---|
| **Measured** | Peer-reviewed research with published numbers | Trust the direction; treat exact figures as population means with wide individual variance |
| **Guideline** | Published industry standard from a platform or body | Reliable within its domain; check the domain matches |
| **Consensus** | Named practitioners agree, no controlled study | Good default, worth departing from deliberately |

The fulldome pacing literature says this about itself: its guidance is *"suggestive based on anecdotal evidence... We do not have comparable research to show how effective such cues are in actual fulldome films shown in real-life settings."* Dome eye-tracking studies have only recently become feasible. Treat pacing rules as accumulated craft, not physics.

---

## Part 1 — Comfort

### Why immersive motion makes people ill

Wide-field optical flow produces **vection** — the visual system concludes the viewer is moving. The vestibular system, correctly, reports stillness. The mismatch is the problem. *(Measured.)*

A refinement that matters for design: it is not the presence of vection but **variability in vection** that drives sickness. A constant, unchanging flow is less provocative than one that starts, stops, and fluctuates. *(Measured.)*

A dome is close to the worst-case geometry, because peripheral vision is what triggers vection and a dome fills it. The same content on a monitor is materially safer than on a dome. *(Measured, indirectly — field-of-view restriction reliably reduces sickness.)*

### Thresholds

| Parameter | Value | Tier | Notes |
|---|---|---|---|
| Sustained rotation | **~20°/s** onset marker | Measured | Two independent sources converge. Individual variance is very wide — standard deviations of 50–70% of the mean. Treat as "starts to matter," not a hard ceiling |
| Multi-axis rotation | Worse than single-axis at the same speed | Measured | **The most robust finding available.** Combining two axes is worse than one; three is not reliably worse than two |
| Roll vs yaw vs pitch | **No reliable difference** | Measured | The hypothesis that roll is worse was explicitly tested and rejected. Do not special-case roll |
| Forward translation | **~1.2 m/s** onset; ~1.4 m/s comfortable walking analogue | Measured / Guideline | NASA's empirical threshold and platform design conventions land in the same place |
| Acceleration vs constant velocity | **Contested** | — | The literature is explicitly unaligned. Practitioner accounts suggest ramp *duration* matters more than magnitude — a long slow ramp is worse than an instant change |
| Onset time | 1–5s, content dependent | Measured | A few seconds of provocative motion can be enough for susceptible viewers |
| Cumulative exposure | Severity compounds over minutes | Measured | Symptoms worsen with continued exposure even when no single moment crosses a threshold |
| Camera pan (large format) | **≤1° of arc per second** | Consensus | Inherited from giant-screen practice; primarily an artifact-avoidance rule, comfort-adjacent |

### Mitigations, ranked by evidence

1. **Provide an earth-fixed horizon.** *(Measured.)* The strongest, most replicated mitigation. Critically, a bare fixation point or crosshair is **not** sufficient — the reference has to convey which way is down. Any sustained motion sequence without a horizon is a design defect.

2. **Keep rotation on one axis.** *(Measured.)* Given that multi-axis is the most robust risk finding, this is the highest-leverage authoring rule in this document.

3. **Give the eye a stable foreground.** *(Measured.)* A near, unmoving element functions as a rest frame the same way a cockpit does in a flight simulator.

4. **Prefer short or immediate speed changes over long ramps.** *(Consensus, contested.)* Theoretically motivated, empirically unsettled. Reasonable default, not a law.

5. **Hold translation near walking pace.** *(Guideline.)* Optical flow well beyond naturalistic self-motion speed is more provocative.

6. **Reduce effective field of view during motion.** *(Measured, with a caveat.)* Vignetting works — except when paired with non-1:1 input gain, where it made things worse. Configuration-dependent.

7. **Slow the camera and minimize cuts.** *(Consensus.)* Standard fulldome guidance.

### Who is in the room

**Susceptibility peaks around ages 9–10**, rising from about age 6 and declining through the teens into adulthood. Adults over 50 report the fewest symptoms. *(Measured.)*

This matters more than any other audience factor for general-admission dome programming. A family show is being watched by the single most susceptible age cohort there is.

**Habituation is real** — regular VR and dome users adapt measurably. *(Measured.)* But a public planetarium audience is mostly first-timers. **Calibrate to the low end of every threshold** unless the audience is known to be experienced.

Sex differences: women report higher *incidence* historically, but under matched controlled exposure, severity did not differ. Treat this as a reporting difference rather than a design variable. *(Measured.)*

### The motion budget

Because severity accumulates, total motion across a runtime is a resource, not just a per-scene property.

There is **no validated numeric budget** — no study establishes "N seconds of flythrough per 25 minutes." What the research does support:

- Track cumulative high-risk time, not only peak intensity
- Concentrated motion is worse than the same total distributed with recovery between
- Every `high` risk effect should be followed by recovery before the next one
- A show that is one continuous flythrough has spent its entire budget in a single instrument

### Do not use ride-safety standards

ASTM F24 amusement-ride standards govern **physical biodynamic acceleration** — real forces on real bodies. They say nothing about visually-induced sickness from projected motion in a stationary seat. Importing those limits here is a category error. The applicable literature is VR and simulator research. *(Stated explicitly to prevent a plausible mistake.)*

### What gets measured

The field standard instrument is the Simulator Sickness Questionnaire, which resolves to three subscales:

| Subscale | Symptoms |
|---|---|
| **Nausea** | Stomach awareness, salivation, sweating, difficulty concentrating |
| **Oculomotor** | Eyestrain, difficulty focusing, headache, blurred vision |
| **Disorientation** | Dizziness, vertigo, head fullness |

Worth knowing: in dome and HMD testing, **oculomotor symptoms typically score highest and nausea lowest.** The earliest signal of a comfort problem is usually eye strain, not sickness. An audience can be uncomfortable well before anyone feels queasy.

---

## Part 2 — Rhythm

### Awe spikes, then resets

Continuous physiological measurement during awe stimuli shows awe presents as **discrete sharp spikes with the fastest recovery-to-baseline of any emotion tested** — roughly 2.4 discrete arousal responses versus 0.9 in a neutral condition, clustering at moments of transition to more expansive views. *(Measured.)*

The design consequence is direct and it is the most important thing in this document:

> **Awe is not a state you can hold an audience in. It is a series of spikes, each requiring a recovery window before the next one can register.**

Attempting to sustain a peak does not produce sustained awe. It produces generic high arousal, which then degrades per the inverted-U relationship between arousal and engagement — and sustained fatigue is documented to drift affect *negative*, not merely flat. *(Measured.)*

A show with five well-spaced peaks and real lulls between them delivers more awe than a show that is loud for twenty-five minutes.

There is **no published number** for how long a peak can be held before fatigue. Anyone quoting one is guessing. What is established is the *shape*: spike, recover, spike.

### The rest beat

Planetarium craft arrived at the same conclusion from the other direction, decades earlier and without the physiology.

At every cornerstone moment — a key fact, a major reveal — **bring the music up, hold a simple image, and stop explaining for five to ten seconds.** *(Consensus.)*

The IPS/GLPA scriptwriting manual puts a rest beat on its final self-edit checklist as a mandatory item: *have you inserted a moment when your audience can simply appreciate the beauty of a star field?* Not a polish step. A requirement.

Named practitioners on the same point: audiences need "thinking time" to absorb before the next thing arrives; a good script "knows when to speak and when not to speak"; there need to be "enough places where we step back and let the brains of our audience do the magic."

Silence is not absence. It is doing the physiological work of letting arousal reset so the next crescendo registers as a fresh spike rather than noise on top of unresolved arousal.

### Pacing numbers

Average Shot Length — runtime divided by number of cuts:

| Medium | ASL |
|---|---|
| Modern feature film | 2–4s |
| 1930s–50s Hollywood | ~11s |
| IMAX / giant screen | 5–21s |
| **Fulldome** | **21–766s** |

Fulldome sits an order of magnitude slower than anything else. Some shows are two shots for an entire runtime. *(Measured — these are counted from released films.)*

Important honesty: fulldome practitioners note this extreme slowness is a **stylistic convention, not a technical requirement.** Faster-cut giant-screen films exist and work. The convention is worth understanding before departing from it, and worth departing from deliberately.

Other published rules of thumb *(all Consensus)*:

| Rule | Value |
|---|---|
| Single image held | no more than ~30s without variation |
| Rest beat | 5–10s at each cornerstone |
| Narration pace | ~100 words per minute — deliberately slower than broadcast |
| Named characters | 2–4 maximum |
| Show objective | statable in ≤25 words |
| Science content | ~25% of script for educational programming |
| Research cut in edit | expect to lose ~90% of gathered material |
| Runtime | 20–45 min; 25–30 most common. Children's programming ~20 min |

### Why cuts hurt on a dome

A hard cut causes **instant subtraction** — whatever the viewer was looking at simply ceases to exist. On a flat screen the eye is already near the centre. On a dome, the audience may have been looking anywhere, and the cut removes their subject without warning. *(Consensus, with a clear mechanism.)*

The alternatives, all in `immersive-effects.md`: Continuous Journey, Match Cut, Orbit Move, Reveal by Occlusion, Lap Dissolve.

Where a cut is necessary, a match cut on the dome must preserve **direction** as well as content — the point of interest should stay in roughly the same region of sky across the edit.

### Directing attention when they can look anywhere

The central dome problem: the audience chooses where to look, and can miss the thing that matters.

Cues ranked by strength *(Consensus, grounded in perceptual research)*:

1. **Motion** — the strongest available cue by a clear margin. Strong enough to mask an edit entirely
2. **Faces and eyes** — evolved salience; the eye finds them before anything else
3. **Brightness and contrast** — processed by the fast visual pathway, pops out pre-attentively. Colour is notably weaker
4. **Looming** — approach is attention-grabbing in a way recession is not; the bias is present in infants
5. **Rack focus** — available to rendered content, less so to fisheye-captured live action
6. **Framing and withheld information** — audiences actively scan for what is being concealed
7. **Focus of expansion** — during camera movement, the eye goes where the camera is heading
8. **Gaze following** — figures in frame looking at something send the audience there
9. **Audio** — theoretically the most precise, but there is no shared audio standard across dome venues, so it travels least reliably. Never make a plot point depend on it alone

**Safe area.** Story-critical content belongs in the region visible from every seat without head-turning. This differs per venue. Concentric seating has no shared forward direction at all — in that geometry, panning a subject around the room to exploit motion salience is a legitimate fallback.

### Shot intent

Fulldome shots divide usefully into three kinds:

| Type | Purpose |
|---|---|
| **Point-of-interest** | Directs attention to something specific |
| **Explorative** | Invites the audience to search the field themselves |
| **Experiential** | Asks only to be inhabited; no information to find |

A show made entirely of point-of-interest shots exhausts the audience. One made entirely of experiential shots has no spine. The mix is the craft.

---

## Part 3 — Arc

### Planetarium six-part structure

The standard model in planetarium scriptwriting *(Consensus)*:

1. **Opening** — the hook. Visual and emotional, causing curiosity
2. **Exposition** — situation and the central question. A story requires an initial tension
3. **Complication** — the question plays out with escalating intensity
4. **Climax** — the confrontation producing irreversible change
5. **Resolution** — consequences, answers
6. **Conclusion** — ideally returning to the opening image

### The four-beat shorthand

> **Bring 'em in · make 'em small · make 'em big · let 'em out**

Welcome, then scale down to smallness against vastness, then the elevation of the climax, then release. Passed hand to hand among planetarians. It fits the awe physiology better than most formal models.

### One climax, cleanly landed

Practitioner preference is for a **single recognizable climax** that ties the show together, rather than several competing peaks — and specifically against a show that "runs out of steam and leaves the audience staring at a blank dome." *(Consensus.)*

No source gives a target *number* of crescendos or a spacing rule. What is established: fulldome's slow cutting and mandatory rest beats structurally bias it toward fewer, more separated peaks than flat cinema, which can sustain multiple mid-film climaxes through rapid cutting.

An epilogue after the apparent ending is risky — audiences applaud at the false ending and are then confused. It can work if the score makes clear more is coming.

### Land softer than the peak

Retrospective judgment of an experience is dominated by its most intense moment and its ending, with the middle largely averaged away. *(Measured — the peak-end rule.)*

Therefore: **the final beat should be gentler than the climax, not a second attempt at it.** A soft landing disproportionately improves how the whole show is remembered, independent of total intensity.

Related, though extrapolated from an adjacent field: peak experiences appear to need a transition window before ordinary stimulus returns. A few minutes of low-arousal material between climax and house lights is the closest evidence-adjacent recommendation available. Dumping an audience from a transcendent finish straight into a bright lobby likely discards part of what was just built. *(Inference — flagged as such.)*

### What actually produces awe

Awe requires two things together *(Measured)*:

- **Vastness** — physical or conceptual
- **Need for accommodation** — it does not fit existing expectation, forcing the mind to update

The second is the one shows forget. Something merely big is not awe-inducing if the audience arrived expecting big. Awe needs the scale to exceed a *calibrated* expectation — which means the show has to establish the expectation first.

Supporting findings:

- Immersive presentation produces measurably more awe than flat presentation of the same content
- Moving through vastness sustains accommodation better than a static vista
- **Urban and natural vastness produce statistically equivalent awe.** Scale and openness matter; biome does not
- Awe expands perceived time availability and reduces impatience — an audience in awe is not impatient, which buys the slow beats their room

---

## Quick reference

**Comfort**
- One rotation axis at a time. Multi-axis is the strongest risk finding
- ~20°/s sustained rotation is where it starts to matter
- Translation near walking pace, ~1.2–1.4 m/s
- Always provide an earth-fixed horizon during motion
- Do not special-case roll — that hypothesis was tested and rejected
- Budget cumulative motion across runtime, not just peaks
- Calibrate to ages 9–10 for general audiences
- Never stack two high-risk effects without recovery

**Rhythm**
- Awe spikes and resets. Build peaks, not plateaus
- 5–10s rest beat at every cornerstone
- No single image beyond ~30s
- Fulldome ASL runs 21s and up — an order of magnitude slower than film
- Avoid hard cuts; prefer journeys, match cuts, orbits, occlusion reveals, dissolves

**Arc**
- Six parts: opening, exposition, complication, climax, resolution, conclusion
- Bring 'em in, make 'em small, make 'em big, let 'em out
- One clean climax beats three competing ones
- End softer than the peak
- Vastness alone is not awe — it has to exceed what the audience was set up to expect
