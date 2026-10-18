# Project video — prompts

A 75-second overview video of the whole project. AI video generators make clips of about 8–10 s, so the video is
a shot list: generate each shot from its prompt, then cut them together with the **real footage we already have**
(`docs/media/*.mp4`, screenshots) in CapCut / Premiere / DaVinci. Real footage is marked **REAL** — never replace
it with generated footage, so nothing in the video shows a result the project has not produced.

## Global style (paste before every shot prompt)

> Clean industrial tech documentary style, soft studio lighting, shallow depth of field, slow smooth camera moves,
> colour palette of deep slate navy (#0C161E), steel teal (#0F4C5C) and forklift yellow (#F5B400), matte light-grey
> floor, no text, no logos, no people's faces, photorealistic, 16:9, 24 fps.

## Shot list

| # | Time | Source | Prompt / footage |
|---|---|---|---|
| 1 | 0–6 s | AI | A miniature warehouse model on a large table, 1:14 scale: two small blue pallet racks, tiny cardboard-loaded pallets, painted lane lines on a matte grey floor, three small yellow toy-sized forklifts parked at charging spots along the back wall. Slow push-in from a low angle. |
| 2 | 6–12 s | AI | Extreme close-up of a small yellow RC forklift's roof: a round black 360° LiDAR sensor spinning, faint red laser dots sweeping across the floor and racks, tiny green status LED ring glowing. Macro lens, slow orbit. |
| 3 | 12–18 s | AI | Close-up of the fork carriage of a small yellow forklift: a tiny camera module tilted down, two steel forks, a black-and-white square ArUco marker on the front of a small blue pallet coming into focus as the forklift approaches slowly. |
| 4 | 18–28 s | **REAL** | `docs/media/rl-docking-simulation.mp4` — the trained policy docking (the "Trained RL policy — rack level 2" scene, with the HUD). Caption: *Trained in simulation · 98.6 % docked*. |
| 5 | 28–38 s | **REAL** | `docs/media/dashboard-live-10s.mp4` — the live fleet map. Caption: *Fleet manager · lane locks · live map*. |
| 6 | 38–48 s | **REAL** | `docs/media/simulation-walkthrough.mp4`, steps 3 and 6 (person stop, lost connection). Caption: *Safety in layers*. |
| 7 | 48–56 s | AI | Inside an electronics bay of a small robot: a compact NVIDIA Jetson-style module board with a heatsink, a tiny blue ESP32 board, neat colour-coded wires, a red emergency-stop mushroom button in the foreground, soft rim light. Slow slide left to right. |
| 8 | 56–64 s | **REAL** | Screenshots `docs/media/screenshots/05-analytics.png` then the floor app (when its screenshots exist), slow Ken-Burns zoom. Caption: *Dashboard · floor app · analytics*. |
| 9 | 64–75 s | AI | Wide shot of the miniature warehouse at dusk light, three small yellow forklifts moving pallets between racks in coordinated lanes, one lifting a pallet onto an upper shelf, camera rising slowly to a top-down view. |
| — | end card | Design | Black background, yellow line: «المخزن الذكي وأسطول الرافعات الذاتية» / *Smart Warehouse & Autonomous Forklift Fleet* · graduation project · team names · university. |

Shots 1, 2, 3, 7, 9 are illustrations of the planned hardware. Label them in the video description as
"concept renders" until real footage of the built forklifts replaces them.

## Voice-over (≈ 70 s)

**العربية:**
> مخزن مصغّر بمقياس واحد إلى أربعة عشر، فيه ثلاث رافعات تتحرك لوحدها.
> كل رافعة تشوف بالليدار والكاميرا، وتقرأ علامة الباليت حتى تدخل الشوكتين بدقة سنتيمتر.
> علّمنا الذكاء الاصطناعي بالمحاكاة: بدأ يقلّد المتحكم الكلاسيكي، وبعدها تفوّق عليه — ٩٨٫٦٪ نجاح مقابل ٩٠٪، وأسرع بـ٣٨٪.
> مدير الأسطول يوزّع المهام ويحجز الممرات حتى ما تتصادم الرافعات.
> والأمان طبقات: زر طوارئ يقطع الكهرباء، معالج يوقف الرافعة خلال مئة ملّي ثانية، وزر «إيقاف الكل» بلوحة المراقبة وبالموبايل.
> المخزن الذكي — مشروع تخرّج.

**English:**
> A 1:14 miniature warehouse with three forklifts that move on their own.
> Each one sees with LiDAR and a camera, and reads a marker on the pallet to slide its forks in within a centimetre.
> We trained the AI in simulation: it first imitated a classical controller, then beat it — 98.6 % docked versus 90 %, and 38 % faster.
> A fleet manager assigns the tasks and reserves the lanes, so the forklifts never collide.
> Safety comes in layers: an emergency stop that cuts the power, a controller that stops within 100 ms, and a Stop-All button on the dashboard and on the phone.
> Smart Warehouse — a graduation project.

## Music

Calm, modern electronic, 100–110 BPM, building slightly at shot 9; duck under the voice-over by −12 dB.
