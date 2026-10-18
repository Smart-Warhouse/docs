# 16 — YOLO perception (camera object detection)

Requirements §6 (PC-06 … PC-08, PC-11), §9 (SF-06), test T-11. Code: `ai/vision` (setup and commands in its
[README](https://github.com/Smart-Warhouse/ai/blob/main/vision/README.md), data provenance in [DATA_SOURCES.md](https://github.com/Smart-Warhouse/ai/blob/main/vision/DATA_SOURCES.md)).
Plan item B6. Sits next to the ArUco layer of [13-ros2.md](13-ros2.md) (`forklift_perception`).

The tooling, a starter model and the inference wrapper are done. The real dataset needs the forklift camera
mounted; when it is, the team only **captures → labels → adds → retrains** with the commands of §3–§5.

## 1. Role and requirements

| ID | Requirement | Where |
|---|---|---|
| PC-06 | YOLO v8n / v11n, classes `person` · `pallet` · `forklift` · `obstacle`, input 640×640, TensorRT FP16 | YOLO11n; class ids 0–3 in that order (`forklift_vision.CLASSES`); ONNX `images` (B, 3, 640, 640) → `jetson/build_trt_engine.sh` |
| PC-07 | ≤ 30 ms per image on the Jetson, ≥ 15 fps | T-11 part 2 (§7), `trtexec` + node rate |
| PC-08 | mAP@0.5 ≥ 0.85 on a test set, `person` recall ≥ 0.95 | T-11 part 1 (§7), `scripts/evaluate.py` |
| PC-11 | warehouse light ≥ 300 lux, tested at 3 light levels | capture protocol (§3), test set covers all 3 |
| SF-06 | person within 1 m of the path → slow / stop | `forklift_vision.geometry` → `person_distance` → `forklift_safety` supervisor (slow < 1 m, stop < 0.5 m) |

ArUco gives the pallet **pose** for docking (PC-03 … PC-05). YOLO answers **what is in front** — people for
SF-06, other forklifts, pallets without a readable marker, and unexpected obstacles.

## 2. Pipeline

```
forklift camera (640×480 @ 30 fps)
  │  forklift_vision.capture  (every 1 s, skip blur / duplicates, one folder per session)
  ▼
datasets/capture/<date>_<robot>_<lux>_<area>/images
  │  CVAT or Roboflow  →  YOLO export  →  forklift_vision.import_labels  (ids remapped by class name)
  ▼
datasets/raw/<pool>/{images,labels}           scripts/check_dataset.py  (≥ 400 img/class, broken labels)
  │  scripts/split_dataset.py  (hash split 70/20/10, stable when pools are added, --chunk keeps sequences together)
  ▼
datasets/<name>/{images,labels}/{train,val,test} + data.yaml
  │  scripts/train.py (YOLO11n, COCO-pretrained, RTX 4050)
  ▼
models/<name>/<name>.pt ──► scripts/export_onnx.py ──► <name>.onnx (opset 17, dynamic batch, 640×640)
  │                                                  │
  │  scripts/evaluate.py (test split: mAP, recall @ deployed threshold, CPU latency)
  ▼                                                  ▼
metrics.json / metrics.md            Jetson: build_trt_engine.sh → <name>_fp16.engine (trtexec --fp16)
                                     ROS 2 node: forklift_vision.detector + geometry → detections, person_distance
```

## 3. Collecting the real dataset (≥ 400 images per class)

**Camera and setting.** The real fork-carriage camera (Pi Camera Module 3, IMX219 or USB fallback) at
640×480, mounted as on the robot (20° down, ME-05), on the real 1:14 warehouse floor with the racks, tape and
walls in place. Images from any other camera or a phone are a different domain — use them only as extras.

**What each class means at 1:14** (requirements §6: people are 1:14 figurines plus real people's feet):

| Class | Capture | Do not label as this class |
|---|---|---|
| `person` | 1:14 figurines (standing, walking, crouching, several colours) **and** real people's feet / shoes / lower legs next to the forklift, at 0.1–2 m, from the front and the side, partly hidden behind pallets | photos/posters of people |
| `pallet` | every pallet type used, empty and loaded, on the floor and on rack level 2, square-on and at 0–90°, 0.1 m (docking) to 2.5 m, marker visible and not visible | the rack shelf |
| `forklift` | the other two forklifts from the front, sides and back, forks down and raised, carrying a pallet, at the charger | the robot's own forks entering the image |
| `obstacle` | anything loose on the floor that is not a pallet or forklift: boxes, cups, tape rolls, cables, tools, toy cones, a fallen load | racks, walls, floor tape, the charger (they are in the map) |

**Light levels (PC-11).** Measure lux at the floor with a lux meter (or a phone app, same phone every time)
and record it with `--lux`. Three levels: **dim ≈ 150 lux** (half the lights), **normal 300–400 lux**
(requirement level), **bright ≥ 600 lux** (all lights + desk lamps). Aim for roughly 25 / 50 / 25 % of the
images, and every level in the test split.

**Sessions.** One capture session per robot × light level × area, e.g. `fl1_lux300_aisleA`. Drive the
forklift slowly (teleop) or move objects between captures; the helper saves a frame every `--interval`
seconds and skips blurred frames and frames that hardly changed:

```bash
python -m forklift_vision.capture --ros-topic /fl1/image_raw --label fl1_lux300_aisleA --lux 300 --robot fl1 --max 300
python -m forklift_vision.capture --source 0 --label bench_lux150 --lux 150 --interval 0.5 --preview   # USB / laptop
```

Plan for ≈ 3 robots × 3 light levels × 2–3 areas × 100–150 frames ≈ 2000–3000 frames. Not every frame holds
every class; check the counts after each labelling batch (`check_dataset.py`) and capture more of the classes
that are short. Keep ≈ 5–10 % background frames (nothing to label, empty label file) — they cut false alarms.

**Split.** `split_dataset.py --chunk 10` puts blocks of 10 consecutive frames of a session into the same
split, so near-duplicate neighbours cannot end up one in train and one in test. The split depends only on
the pool and file names: adding new pools later never moves an existing test image into training.

## 4. Labelling (CVAT or Roboflow) and import

Rules for both tools:

- Exactly these labels: `person`, `pallet`, `forklift`, `obstacle` (the import maps by **name**, so order and
  capitalisation do not matter; other names stop the import unless `--map old=new` / `--drop-unknown`).
- Rectangle around the **visible** part of the object, tight. Partly hidden or cut by the image edge: label the
  visible part if you can tell what it is (≈ 25 % visible).
- `pallet` box includes its load. `forklift` box includes mast, forks and any carried pallet's overlap.
- Label every instance in the frame — an unlabelled person teaches the model to ignore people.
- Frames with nothing to label stay in the set with an empty label file.

**CVAT** (cvat.ai or self-hosted): create a project with the 4 labels (rectangle), create a task per capture
session and upload `datasets/capture/<session>/images`, annotate (the *track* mode interpolates boxes between
frames of a slowly moving object), then *Export task dataset* → **YOLO 1.1** (or *Ultralytics YOLO Detection
1.0*), images optional. Import:

```bash
python -m forklift_vision.import_labels --src exports/fl1_lux300_aisleA --images datasets/capture/<session>/images \
    --dst datasets/raw/fl1_lux300_aisleA
```

**Roboflow**: create an *Object Detection* project with the 4 classes, upload the session images, label,
*Generate* a version **without** preprocessing resize and **without** augmentation (we split and augment
ourselves), *Export* → **YOLOv8** (or YOLOv11) zip, unzip, then the same `import_labels` command without
`--images` (the export contains them). Roboflow's own train/valid/test split is ignored on purpose — our hash
split decides.

Then `python scripts/check_dataset.py datasets/raw/<pool>` and fix what it lists (missing / invalid / orphan
labels). A second person should review ≈ 10 % of the boxes of each pool.

## 5. Training, export, TensorRT

```bash
python scripts/split_dataset.py --out datasets/forklift_v1 --chunk 10 datasets/raw/fl* datasets/raw/bench*
python scripts/check_dataset.py datasets/forklift_v1 --strict
python scripts/train.py --data datasets/forklift_v1/data.yaml --name forklift_v1 --epochs 100
python scripts/export_onnx.py models/forklift_v1/forklift_v1.pt --parity-images datasets/forklift_v1/images/test
python scripts/evaluate.py --weights models/forklift_v1/forklift_v1.pt --data datasets/forklift_v1/data.yaml \
    --label "forklift_v1 — real test split (PC-08)"
```

Mixing in the starter pools (`datasets/raw/synth_mujoco`, `coco_person`) is optional: try with and without and
keep what scores better on the **real** test split — evaluate on real images only (`evaluate.py` reports per
source, so a mixed test split still shows the real-camera numbers separately).

Training choices: YOLO11n COCO-pretrained (PC-06 allows v8n or v11n; 11n is ≈ as fast and a bit more
accurate), 640×640, mosaic, horizontal flip only (camera is upright), HSV value jitter ±50 % for the light
levels, early stop after 15 epochs without improvement. On the RTX 4050 (6 GB) batch 16 uses ≈ 4 GB.

ONNX: opset 17, `images` float32 (B, 3, 640, 640) RGB 0–1, output `output0` (B, 8, 8400) = cx, cy, w, h (input
pixels) + 4 sigmoid class scores; batch dynamic, H×W fixed at 640; class names in the ONNX metadata. On the
Jetson (JetPack 6.2, TensorRT 10.3):

```bash
sudo nvpmodel -m 0 && sudo jetson_clocks            # MAXN SUPER
./build_trt_engine.sh forklift_v1.onnx              # trtexec --fp16, profile 1..MAX_BATCH ×3×640×640, then a 15 s benchmark
```

Engines are tied to the GPU and TensorRT version: always build on the Jetson itself.

## 6. Wrapper API for the ROS 2 node

`forklift_vision` is pure Python (numpy, OpenCV, onnxruntime; works with numpy < 2 and the Jetson's OpenCV 4.5),
no rclpy, no torch — the node is a thin wrapper like the others in `robot/ros2_ws` (not written yet).

```python
from forklift_vision.detector import YoloOnnxDetector, Detection
from forklift_vision.geometry import Camera, nearest_distance

det = YoloOnnxDetector(path, conf_thres=0.25, iou_thres=0.7, max_det=100,
                       providers=["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"])
dets: list[Detection] = det(bgr_image)    # class_id, class_name, score, x1, y1, x2, y2 in ORIGINAL pixels; .xyxy, .center
det.detect_batch([img1, img2])            # one inference call
cam = Camera.from_k(camera_info.k, camera_info.width, camera_info.height,
                    height_m=0.054 + lift_m, pitch_rad=0.349)       # forklift_description dimensions.yaml
person_distance = nearest_distance(cam, dets, "person", min_score=0.25)   # inf when no person
```

- Pre/post-processing is the Ultralytics one: letterbox to 640×640 (grey 114, same rounding), BGR → RGB, /255,
  confidence filter, class-aware NMS (IoU 0.7 default, like Ultralytics `predict`), boxes mapped back and
  clipped. `export_onnx.py --parity-images` compares the wrapper with Ultralytics on real images.
- A pure TensorRT backend (python `tensorrt` + the `.engine`) reuses `preprocess()` and `postprocess()` around
  its own `execute`; onnxruntime-gpu with the TensorRT execution provider (Jetson Zoo wheel) needs no extra code.
- `Camera` / `nearest_distance`: flat-floor pinhole model from the bottom-centre of the box (the feet). A box cut
  by the bottom edge returns the bottom row's floor distance (< 0.1 m on the 1:14 robot), i.e. a stop.

Proposed node `forklift_perception/yolo_node.py`: in `image_raw`, `camera_info`, fork lift height
(`ForkState`); out `detections` (`vision_msgs/Detection2DArray`), `person_distance` (`std_msgs/Float32`,
`inf` when nobody, published every frame so the supervisor's 0.5 s timeout sees a live detector). Then set
`person_detector_required: true` in `forklift_bringup/config/forklift.yaml`.

## 7. Acceptance test T-11 (PC-07, PC-08)

**Part 1 — accuracy (PC-08)**, laptop:

1. Test split = the 10 % hash split of the real dataset (≥ 40 images per class, all 3 light levels, all
   robots); nobody looks at it while tuning.
2. `scripts/evaluate.py --weights models/<final>/<final>.pt --data datasets/<final>/data.yaml`.
3. Pass: `mAP@0.5 (all) ≥ 0.85` (Ultralytics column) **and** `person recall ≥ 0.95` in the ONNX-wrapper column
   at the threshold the robot uses (conf 0.25, IoU 0.5 match). If recall is short, lower `conf_thres` for
   `person` in the node and re-run — report the threshold used.
4. Repeat per light level (copy each level's test images into a folder) to show PC-11 holds at all three.

**Part 2 — speed (PC-07)**, Jetson in MAXN SUPER:

1. `build_trt_engine.sh <final>.onnx` → pass when trtexec `GPU Compute Time` mean ≤ 30 ms.
2. In the running node: end-to-end rate (preprocess + inference + postprocess) ≥ 15 fps with the camera at 30 fps,
   measured over 60 s (`ros2 topic hz /fl1/person_distance`).

Record both in the table below with date, model and commit.

| Date | Model | mAP@0.5 | person recall | GPU compute (ms) | node fps | Pass |
|---|---|---|---|---|---|---|
| – | (real data not collected yet) | | | | | |

## 8. Starter model (non-final data — NOT the PC-08 result)

`models/starter_v1` exists to run the pipeline end-to-end before the camera is mounted. Data (details and
licences in [DATA_SOURCES.md](https://github.com/Smart-Warhouse/ai/blob/main/vision/DATA_SOURCES.md)): 587 COCO val2017 images of people (CC BY /
BY-SA / no known restrictions only) + 1800 MuJoCo renders of the 1:14 scene with exact boxes from the
segmentation render, 601 of them with COCO person cut-outs pasted in. 2387 images, split 1694 / 471 / 222.

Training: YOLO11n COCO-pretrained, 40 epochs, 640, batch 16, RTX 4050 Laptop, **31.1 min** (Ultralytics
8.4.182, torch 2.14.1+cu126). Files: `starter_v1.pt` 5.5 MB, `starter_v1.onnx` 11.2 MB (FP32).

Held-out test split (222 images, 812 boxes), `scripts/evaluate.py`, 2026-10-18:

| class | mAP@0.5 | mAP@0.5:0.95 | precision @0.25 | recall @0.25 |
|---|---|---|---|---|
| person | 0.770 | 0.567 | 0.797 | 0.680 |
| pallet | 0.850 | 0.751 | 0.789 | 0.797 |
| forklift | 0.883 | 0.754 | 0.774 | 0.801 |
| obstacle | 0.890 | 0.787 | 0.824 | 0.824 |
| **all** | **0.848** | **0.715** | | |

- Person recall at conf 0.25 by source: COCO photos 0.566 (90/159 — many small, distant, partly hidden people
  in street scenes), synthetic scene with pasted people 0.931 (67/72). At conf 0.10: 0.736 overall
  (COCO 0.648, synthetic 0.931), person precision 0.651.
- The synthetic classes score high because test renders come from the same generator; this says the labels
  and training are consistent, not that the model works on the real camera.
- ONNX wrapper vs Ultralytics on 60 test images (same 640×640 letterbox): 122/122 boxes matched, mean IoU
  0.9998, min 0.994.
- CPU latency here (i9-13900H, onnxruntime 1.31 CPU, batch 1, 640×480 frame): 28.3 ms mean / 31.7 ms p95
  end-to-end (preprocess 5.6, inference 22.4, postprocess 0.3) → 35 fps, measured with the laptop otherwise
  quiet; with other jobs holding the CPU at ≈ 73 % it was 74 ms mean. Ultralytics on the RTX 4050: 3.4 ms
  inference. The Jetson number (PC-07) needs the board.

PC-08 is **not** met on this data: mAP@0.5 0.848 is just under 0.85 on a mostly synthetic test split, and
person recall 0.68 is far below 0.95. Only the real-camera dataset can decide PC-08.

## 9. Limitations and next steps

- The starter domain is far from the real one: COCO people are full-size adults, the renders are flat-shaded
  geometry with placeholder dimensions. Expect a large drop on the real camera until real data is added.
- `obstacle` is open-ended; the real list of things that end up on the floor decides how well it generalises.
- Person distance assumes a flat floor and visible feet; a person behind a pallet is detected but placed at the
  pallet's foot line or further.
- Write `yolo_node.py` (§6), measure PC-07 on the Jetson, then collect and label the real data (§3–§4).
