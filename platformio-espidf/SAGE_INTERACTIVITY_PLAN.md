# AN/FSQ-7 SAGE Simulator - Interactivity Enhancement Plan

## Overview
This document outlines improvements to make the SAGE simulator more interactive, educational, and realistic based on user feedback.

---

## 1. CPU Core Execution Visualization

### Current Problem
- Programs load and run, but user can't see what's happening
- No indication of what the program computed
- Unclear whether execution succeeded or failed

### Solution: Real-Time Execution Panel

```
┌─────────────────────────────────────────────────┐
│ EXECUTION TRACE                                 │
├─────────────────────────────────────────────────┤
│ Step 1: LDA 1.0010  ← Load A from address 0010 │
│         A = 00050000 (value: 5)                 │
│                                                 │
│ Step 2: ADB 1.0011  ← Add to A from addr 0011  │
│         A = 000A0000 (value: 10)                │
│                                                 │
│ Step 3: STA 1.0012  ← Store A to address 0012  │
│         Memory[0012] = 000A0000                 │
│                                                 │
│ Step 4: HLT         ← Program halted            │
│                                                 │
│ RESULT: Sum = 10 stored at address 0012        │
└─────────────────────────────────────────────────┘
```

**Features:**
- Instruction-by-instruction trace with human-readable descriptions
- Register values shown after each operation
- Memory addresses accessed highlighted
- Final result displayed clearly
- Speed control: Real-time / Slow / Step-by-step

---

## 2. Light Gun System (Target Selection)

### Current Problem
- Light gun coordinates tracked but nothing happens
- No visual feedback when clicking targets
- Unclear what light gun is for

### Solution: Target Designation System

**Workflow:**
1. **Arm Light Gun**: Click "DESIGNATE" button on SD Console
2. **Crosshair Appears**: Cursor changes to crosshair over radar
3. **Click Target**: Click on radar blip
4. **Target Selected**: 
   - Target highlights in yellow
   - Target info appears in DD CRT panel
   - Intercept can be launched

**Visual Feedback:**
```
┌──────────────────────────────────┐
│  RADAR DISPLAY                   │
│                                  │
│        ◉ ← Selected (yellow)     │
│      ╱   ╲                       │
│    ╱       ╲ ← Crosshair        │
│  ●   ●   ●  ← Other targets     │
│                                  │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  DD CRT - SELECTED TARGET        │
│  ┌────────────────────────────┐  │
│  │ TGT-1004  [MISSILE]        │  │
│  │ ALT: 35,000 ft             │  │
│  │ SPD: 795 kts (MACH 1.2)    │  │
│  │ HDG: 066° (NE)             │  │
│  │ THREAT: HIGH               │  │
│  │                            │  │
│  │ [LAUNCH INTERCEPT]         │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

---

## 3. Geographic Radar Display

### Current Problem
- Targets appear in abstract space
- No geographic context
- Movements seem random

### Solution: North American Defense Scope

```
┌─────────────────────────────────────────────────┐
│                    RADAR SCOPE                  │
│                                                 │
│        CANADA                                   │
│          ╱‾‾‾╲                                 │
│     ╱‾‾‾      ‾‾‾╲    ●←incoming (RED)        │
│   ╱              ╲                            │
│  │  Great Lakes   │   ●←bomber (YELLOW)       │
│  │     ~~~         │                           │
│   ╲  ┌───┐        │   ◉←friendly (GREEN)     │
│    ╲ │NY │       ╱                            │
│     ╲└───┘  ___╱                              │
│      ╲___  ╱  ← East Coast                    │
│          ╲╱                                    │
│        Atlantic Ocean                          │
│                                                 │
│  Range Rings: 100mi, 200mi, 300mi              │
│  Bearing: 0°(N), 90°(E), 180°(S), 270°(W)     │
└─────────────────────────────────────────────────┘
```

**Features:**
- East Coast outline (Boston to DC)
- Great Lakes region
- Major cities marked
- Range rings with distance
- Bearing indicators
- Targets move along realistic flight paths
- Bombers coming from Arctic (over Canada)
- Friendly aircraft patrol patterns

---

## 4. Functional SD Console Controls

### Current Problem
- Buttons clickable but do nothing
- Purpose unclear

### Solution: Category Filtering & Display Control

**CATEGORY SELECT (S1-S13):**
- S1: Show ALL targets
- S2: FRIENDLY only (green)
- S3: UNKNOWN only (yellow)
- S4: HOSTILE only (red)
- S5: MISSILES only
- S6: BOMBERS only
- S7: FIGHTERS only
- S8-S13: Altitude filters (LOW/MEDIUM/HIGH)

**FEATURE SELECT (S20-S24):**
- S20: Show flight paths (trailing line)
- S21: Show intercept vectors
- S22: Show range circles
- S23: Show altitude grid
- S24: Show callsigns

**OFF-CENTERING BUTTONS:**
- Pan radar view in 8 directions
- Zoom in/out on specific areas
- Return to center button

**BRIGHT-DIM:**
- Adjust scope brightness (affects trail visibility)

**Visual feedback:** Each button lights up when pressed, selected filters show in status bar

---

## 5. Vacuum Tube Maintenance System

### Current Problem
- Tubes fail but nothing happens
- No way to interact with tube system

### Solution: Tube Rack Maintenance Mini-Game

```
┌─────────────────────────────────────────────────┐
│          VACUUM TUBE RACK #3 (FAILED)           │
├─────────────────────────────────────────────────┤
│  Row A: │▓│▓│▓│▓│▒│▓│▓│▓│  ← Dimming (▒)      │
│  Row B: │▓│▓│✗│▓│▓│▓│▓│▓│  ← Failed (✗)       │
│  Row C: │▓│▓│▓│▓│▓│▓│▓│▓│  ← Good (▓)          │
│  Row D: │▓│▓│▓│✗│▓│▓│▓│▓│                      │
│         └─┴─┴─┴─┴─┴─┴─┴─┘                      │
│                                                 │
│  Click failed tube to replace                   │
│  Warning: 2 tubes failed, 1 tube degraded       │
│  System performance: 87% (tube health)          │
└─────────────────────────────────────────────────┘
```

**Replacement Flow:**
1. Failed tube blinks red
2. Click tube → "Pull Tube" animation (2 sec)
3. "Insert New Tube" animation (2 sec)  
4. Warmup animation (glow increases over 5 sec)
5. System performance restored

**Effects of Failed Tubes:**
- CPU runs slower
- Radar refresh rate drops
- Display flickers
- Memory errors (program crashes)
- Too many failures → System OFFLINE

**Proactive Maintenance:**
- Tubes degrade over time (▓ → ▒ → ✗)
- Click degraded tube to replace before failure
- "Tube Health Monitor" shows system-wide status

---

## 6. Realistic Radar Tracking

### Current Problem
- Targets appear randomly
- Movements implausible
- Threat assessment unclear

### Solution: Scenario-Based Target Generation

**Scenario 1: Bomber Raid**
- Formation of 3-5 bombers approaching from Arctic
- Altitude: 35,000-45,000 ft (high altitude)
- Speed: 450-600 kts
- Bearing: 180° (southbound toward NYC)
- Threat: HIGH
- Escorts: 2 fighters per bomber

**Scenario 2: Missile Attack**
- Single ICBM launches detected
- Altitude: 60,000+ ft (ballistic trajectory)
- Speed: 800+ kts (Mach 1.5+)
- Bearing: Direct line to target city
- Threat: CRITICAL
- Time to impact: Countdown shown

**Scenario 3: Routine Patrol**
- Friendly CAP (Combat Air Patrol) aircraft
- Altitude: 20,000-30,000 ft
- Speed: 300-400 kts
- Flight pattern: Racetrack orbit over sector
- Threat: NONE

**Scenario 4: False Alarm**
- Commercial airliner strays into ADIZ
- Altitude: 35,000 ft (commercial cruising)
- Speed: 450 kts
- Transponder: Eventually IFF's as FRIENDLY
- Threat: LOW → NONE (after identification)

**Target Behavior:**
- Smooth position updates (not jumpy)
- Altitude/speed changes gradual
- Missiles home in on targets (vector changes)
- Aircraft maintain heading unless intercepted
- Targets disappear at coastline (simulate exit)

---

## 7. Interactive Tutorial System

### Current Problem
- New users don't know what to do
- Controls not obvious
- No guidance

### Solution: Training Mode

**On First Launch:**
```
┌─────────────────────────────────────────────────┐
│       WELCOME TO AN/FSQ-7 SAGE SIMULATOR        │
├─────────────────────────────────────────────────┤
│                                                 │
│  This is a historically accurate simulation of  │
│  the 1950s SAGE (Semi-Automatic Ground          │
│  Environment) air defense computer system.      │
│                                                 │
│         [ START TRAINING MODE ]                 │
│         [ SKIP TO OPERATION ]                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Training Missions:**

**Mission 1: Power-On Sequence**
- Objective: Start the computer
- Guide: "Click POWER ON button"
- Wait for tube warmup
- Explain status indicators

**Mission 2: Target Selection**
- Objective: Designate a target with light gun
- Guide: "Click DESIGNATE, then click target"
- Show target info in DD CRT
- Explain threat levels

**Mission 3: Launch Intercept**
- Objective: Launch interceptor at hostile bomber
- Guide: "Select hostile target, click LAUNCH INTERCEPT"
- Watch intercept vector
- Confirm intercept success

**Mission 4: Console Operations**
- Objective: Use SD Console filters
- Guide: "Press S4 to show only HOSTILE targets"
- Try different category filters
- Use off-centering to pan view

**Mission 5: Tube Maintenance**
- Objective: Replace failed tube before system fails
- Guide: "Click blinking red tube in rack"
- Complete replacement procedure
- Restore system health

**Mission 6: CPU Programming**
- Objective: Load and run a target calculation program
- Guide: "Select program, click LOAD, click RUN"
- Watch execution trace
- See computed result

**Help Overlay (Press 'H' key):**
```
┌─────────────────────────────────────────────────┐
│  KEYBOARD SHORTCUTS                             │
│  H - Show/hide this help                        │
│  Space - Pause/resume simulation                │
│  D - Toggle DESIGNATE mode (light gun)          │
│  R - Reset view to center                       │
│  1-9 - Quick select radar filter                │
│  T - Open tube maintenance                      │
│  C - Open CPU trace panel                       │
│  ESC - Clear selection                          │
└─────────────────────────────────────────────────┘
```

---

## 8. CPU Program Output Panel

### Current Problem
- Program runs but no visible output
- Can't see computation results
- Unclear if program worked correctly

### Solution: Console Output Window

```
┌─────────────────────────────────────────────────┐
│  CONSOLE OUTPUT                                 │
├─────────────────────────────────────────────────┤
│  Program: Array Sum (Authentic)                 │
│  Status: ✓ COMPLETED                            │
│  Runtime: 147 cycles                            │
│                                                 │
│  INPUT:                                         │
│    Array at 1.0010-1.0014: [5, 10, 15, 20, 25] │
│                                                 │
│  COMPUTATION:                                   │
│    5 + 10 = 15                                  │
│    15 + 15 = 30                                 │
│    30 + 20 = 50                                 │
│    50 + 25 = 75                                 │
│                                                 │
│  OUTPUT:                                        │
│    Sum = 75 (stored at address 1.0015)          │
│    Accumulator final value: 00004B00            │
│                                                 │
│  ✓ All tests passed                             │
└─────────────────────────────────────────────────┘
```

**For Different Programs:**

**Coordinate Conversion:**
```
INPUT:  Radar coordinates (range, bearing)
        Range = 150 miles, Bearing = 045°
        
OUTPUT: Cartesian coordinates (X, Y)
        X = 106.1 miles (East)
        Y = 106.1 miles (North)
        Target position: Northeast quadrant
```

**Subroutine Example:**
```
CALL STACK:
  main() → calc_trajectory()
           → compute_angle()
           ← return: 32°
         → compute_range()
           ← return: 180 miles
       ← return: intercept point (127, 127)

RESULT: Intercept coordinates calculated
```

---

## Implementation Priority

### Phase 1 (High Impact):
1. **Geographic radar display** - Makes simulation immediately more realistic
2. **Light gun target selection** - Core interaction loop
3. **CPU execution trace panel** - Shows what programs do

### Phase 2 (Enhanced Experience):
4. **Tutorial system** - Onboarding for new users
5. **Functional SD Console** - Deepens interaction
6. **Console output panel** - Program results

### Phase 3 (Depth):
7. **Realistic radar scenarios** - Better tracking behavior
8. **Tube maintenance mini-game** - Adds maintenance dimension

---

## Technical Notes

### UI Components Needed:
- Execution trace panel (collapsible)
- Console output window (modal/sidebar)
- Help overlay (keyboard shortcut)
- Tutorial dialog system
- Target selection highlight shader
- Crosshair cursor mode
- Geographic SVG overlay for radar
- Tube rack grid component

### State Management:
- Selected target ID
- Light gun mode (armed/disarmed)
- Active radar filters
- Tutorial progress
- Tube health array
- Execution trace buffer

### Animation Considerations:
- Smooth target movement (interpolation)
- Tube replacement sequence
- Intercept missile path
- Radar sweep effect
- Register value changes (highlight flash)

---

## User Experience Flow

**Typical Session:**
1. Power on → Watch warmup sequence
2. Radar activates → Targets appear over coastline
3. Hostile bomber formation detected → Alert!
4. Press 'D' → Arm light gun
5. Click bomber → Target selected, info shows
6. Click "LAUNCH INTERCEPT" → Missile launches
7. Watch intercept → Success! Target eliminated
8. Meanwhile: Tube fails (warning light)
9. Open tube rack → Click failed tube → Replace
10. Load CPU program → Watch trace → See result
11. Filter radar to show only missiles
12. Pan view to focus on threat sector

**Educational Value:**
- Learn Cold War air defense concepts
- Understand vacuum tube computer operations
- Experience 1950s human-computer interaction
- Appreciate the scale of SAGE system

---

## Conclusion

These enhancements transform the simulator from a technical demonstration into an interactive, educational experience. Users will understand:
- **What** the SAGE system did (air defense)
- **How** operators interacted with it (light gun, console)
- **Why** it was significant (real-time computing, human factors)

The simulator becomes a playable history lesson about one of the most ambitious computing projects ever built.
