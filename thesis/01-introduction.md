# Chapter 1 — Introduction

<!--
Draft generated from the repository on 2026-10-18. Every number carries a comment with the file it comes from.
Placeholders: [TEAM MEMBERS], [SUPERVISOR], [UNIVERSITY], [DEPARTMENT], [DATE]. Items needing review: [CHECK].
-->

**[UNIVERSITY] · [DEPARTMENT]**
**Graduation project, [ACADEMIC YEAR]**
**Team:** [TEAM MEMBER 1], [TEAM MEMBER 2], [TEAM MEMBER 3], [TEAM MEMBER 4]
**Supervisor:** [SUPERVISOR]
**Submitted:** [DATE]

---

## ملخص

يقدّم هذا المشروع «المخزن الذكي وأسطول الرافعات الذاتية»: مخزناً مصغّراً بمقياس 1:14 تعمل فيه ثلاث رافعات شوكية ذاتية
(ورافعة رابعة احتياطية) تنقل الباليتات بين الرفوف ومناطق الاستلام والشحن من دون تدخل بشري، تحت إشراف خادم مركزي
للأسطول ونظام لإدارة المخزون (WMS) ولوحة مراقبة حية وتطبيق ميداني للهاتف. الرافعة مبنية على هيكل Huina 1577 Pro
مع حاسوب Jetson Orin Nano Super لتشغيل ROS 2 والملاحة والإدراك، ومتحكم ESP32-S3 يشغّل حلقة أمان بتردد 1 kHz
مستقلة عن الحاسوب، وليدار RPLIDAR C1 وكاميرا وحلقة من ستة حساسات ToF.

بُنيت السلامة بطبقات مستقلة: زر طوارئ يقطع طاقة المحركات بالعتاد، ثم منطق ToF والـ Watchdog على ESP32، ثم مشرف
أمان على Jetson يقيّد كل مصادر الأوامر، ثم أقفال الممرات وزر «إيقاف الكل» على الخادم. يوزّع الخادم المهام
بخوارزمية الأقرب أو بالخوارزمية الهنغارية، ويمنع التصادم بأقفال على عقد ومقاطع شبكة الممرات مع كشف الانسداد وحلّه.

دُرّبت سياسة تعلّم معزّز لإدخال الشوكة في البالية داخل محاكٍ فيزيائي (MuJoCo). فشل PPO المجرد والتدريب المتدرج
(Curriculum) في تحقيق أي نجاح، بينما نجح الجمع بين التعلم بالمحاكاة (Behaviour Cloning) من متحكم كلاسيكي ثم الضبط
الدقيق بـ PPO: على 1000 حالة عشوائية حققت السياسة 98.6% نجاحاً مقابل 90% للمتحكم الكلاسيكي، بزمن متوسط
6.4 ث مقابل 10.3 ث. كل البرمجيات مختبرة على الحاسوب وفي التكامل المستمر (CI)؛ أما اختبارات العتاد T-01..T-16 فهي
مخططة وتُنفَّذ بعد تجميع الرافعة الأولى.

**الكلمات المفتاحية:** أسطول روبوتات ذاتية، رافعة شوكية، إدارة المخزون، ROS 2، التعلم المعزّز، إدارة المرور، السلامة.

<!-- sources: docs/00-sources/system-requirements.md §1, §9; docs/11-simulation-training.md §4 (98.6 %, 90 %, 6.4 s, 10.3 s);
     code/training/models/docking_v3/meta.json eval_1000; code/training/models/baseline_eval.json; plan.md Track C -->

## Abstract

This project builds a 1:14-scale smart warehouse in which three autonomous forklifts (plus one spare) move pallets
between racks, inbound docks and outbound docks without human intervention. A central fleet manager with a
warehouse management system (WMS), a live web dashboard and a floor-operator mobile app supervise the fleet. Each
forklift is a modified Huina 1577 Pro RC forklift carrying an NVIDIA Jetson Orin Nano Super (ROS 2, navigation,
perception), an ESP32-S3 microcontroller (a 1 kHz safety and motor-control loop that does not depend on the Jetson),
an RPLIDAR C1, a camera and a ring of six time-of-flight (ToF) distance sensors. Safety is layered so that each layer
works when the one above it fails. Fleet traffic is controlled on a lane graph with per-node and per-lane locks and
deadlock resolution. A reinforcement-learning (RL) policy for the final pallet-docking manoeuvre was trained in a
MuJoCo simulator: plain PPO and a curriculum both failed, while behaviour cloning from a classical controller followed
by conservative PPO fine-tuning docked 98.6 % of 1000 randomised test episodes against 90.0 % for the classical
controller, in 6.4 s instead of 10.3 s on average. All software is tested on the host and in continuous integration;
hardware acceptance tests T-01 … T-16 are planned and will be run once the first forklift is assembled.

<!-- sources: as above; docs/01-architecture.md; plan.md -->

---

## 1.1 Problem

Warehouses spend much of their labour moving pallets between storage and docks. Automated guided vehicles and
autonomous mobile robots (AMRs) take over this work in large facilities, but they bring three hard problems at
once:

1. **Each vehicle must be precise.** Inserting forks into a pallet leaves only a few millimetres of clearance;
   in our 1:14 model the forks have **1.75 cm of clearance per side**.
   <!-- docs/11-simulation-training.md §4 "the forks have only 1.75 cm clearance per side" -->
2. **Many vehicles must share narrow aisles** without collisions and without blocking each other permanently
   (deadlock).
3. **People work beside the vehicles**, so every motion has to be bounded by safety mechanisms that keep working
   when software, computers or the network fail.

Full-scale industrial systems are expensive and closed, which makes them hard to study in a university setting.
A scale model allows the complete chain — mechanics, electronics, embedded control, robot software, fleet
management, user interfaces and machine learning — to be built and tested by a student team.

## 1.2 Idea

Build the whole system at 1:14 scale with off-the-shelf RC forklifts and open-source software, keeping the
architecture of a real installation:

- **Robot:** a modified Huina 1577 Pro (52.4 × 18.7 × 31.7 cm) with its original chassis, motors and lift kept, the
  RC receiver and battery replaced, and sensors and computers added.
  <!-- docs/00-sources/system-requirements.md §2 -->
- **Server:** a fleet manager that assigns tasks and grants lanes, plus a WMS that tracks every pallet.
- **Interfaces:** a control-room dashboard (with a kiosk mode for a large screen) and a phone app for people on
  the floor.
- **AI:** an RL policy for the last ≈ 40 cm of pallet docking, which must beat a classical controller before it is
  allowed to replace it.
  <!-- docs/00-sources/system-requirements.md §7 ("الاقتراب النهائي … آخر ≈ 40 سم") and §8 -->

## 1.3 Objectives

The objectives follow the functional requirements of the project specification
(<!-- docs/00-sources/system-requirements.md §1 --> FR-01 … FR-12):

| # | Objective | Requirement ids |
|---|---|---|
| O1 | Accept a move order from the dashboard or the WMS and assign it to an available forklift automatically | FR-01, FR-02 |
| O2 | Drive autonomously to the target location on the warehouse map, avoiding obstacles | FR-03 |
| O3 | Detect the pallet, insert the forks, lift and set it down | FR-04 |
| O4 | Keep the WMS consistent: a pallet's location changes only after a completed move | FR-05, SV-09 |
| O5 | Show position, state and battery of every forklift live | FR-06 |
| O6 | Stop for people and obstacles and continue afterwards; prevent forklift–forklift collisions in lanes | FR-07, FR-08 |
| O7 | Send forklifts to charge on low battery; offer manual (gamepad) control with safety still active | FR-09, FR-10 |
| O8 | Report tasks, times, utilisation and faults | FR-11 |
| O9 | Train an RL docking policy that is more accurate or faster than the classical controller | FR-12, AI-04, AI-07 |

Quantitative targets (non-functional requirements) include localisation error ≤ 3 cm / 3°, docking alignment
≤ 1 cm / 2°, maximum speed 0.3 m/s, hazard stop ≤ 100 ms, ≥ 45 min per charge, ≥ 90 % task success without
intervention, and safety that keeps working when the Jetson or the Wi-Fi fails.
<!-- docs/00-sources/system-requirements.md §1 NFR-01..NFR-08 -->

## 1.4 Scope

**In scope.**

- A 1:14 warehouse floor of **6 m × 4 m** with two racks (16 rack locations on two levels), 2 inbound docks, 2
  outbound docks, 2 staging spots and 4 chargers. *The coordinates are placeholders until the real floor is
  measured (EN-01, EN-08).*
  <!-- docs/04-data-model.md "Lane graph" -->
- Three working forklifts and one spare that can be added by configuration only (NFR-09).
- The complete software stack: ESP32-S3 firmware, nine ROS 2 packages, fleet server + WMS, dashboard, floor app,
  public landing page, docking simulator and training pipeline.
  <!-- docs/01-architecture.md "Code map"; docs/13-ros2.md §1 -->
- A parts budget of about **1,507,250 IQD per forklift** (the Jetson alone is 995,000 IQD).
  <!-- plan.md A1; code/landing/src/content/bom.ts BOM_TOTAL_IQD, BOM_JETSON_IQD -->

**Out of scope.** Full-scale vehicles, outdoor operation, mixed traffic with other vendors' robots, a production
security model beyond per-robot broker credentials and role-based access, and certification against industrial
safety standards [CHECK: decide whether the thesis should mention ISO 3691-4 as context only].

**State of the work at the time of writing.** All software is written and tested on the host and in CI. The
hardware (parts order, measurement of the first forklift, wiring, the floor) is the critical path and has not been
done yet, so every result that depends on hardware is reported as **planned** (Chapter 7).
<!-- plan.md "Blocked — needs you", Track A, Track C -->

## 1.5 Contributions

1. A layered-safety architecture for a small forklift fleet in which each layer works without the layers above it
   (Chapter 3).
2. A lane-graph fleet manager with all-or-nothing lock acquisition, wait-for-graph deadlock detection and detour /
   back-off resolution, and a runtime-switchable task allocator (Chapter 5).
3. A docking simulator and a training recipe — imitation from a classical controller, then conservative PPO
   fine-tuning with validation-based checkpoint selection — that passes the AI-04 gate where plain PPO and a
   curriculum failed (Chapter 4).
4. A software verification approach in which all decision logic is plain code tested without hardware, leaving thin
   hardware adapters for the bench (Chapter 6).

## 1.6 Thesis structure

| Chapter | Content |
|---|---|
| 2 | Related work: autonomous forklifts, AMR fleets, Nav2, ArUco pose estimation, RL for docking |
| 3 | System design: layers, hardware, firmware, ROS 2, server, apps |
| 4 | Simulation and AI: the docking environment, failed and successful training, results |
| 5 | Fleet management: lane graph, locks, deadlocks, task allocation |
| 6 | Software verification: tests per part, CI, host-verified vs pending hardware |
| 7 | Hardware validation plan: tests T-01 … T-16 |
| 8 | Conclusion and future work |

Figures referenced in the chapters live in [`docs/media/`](../media/).
